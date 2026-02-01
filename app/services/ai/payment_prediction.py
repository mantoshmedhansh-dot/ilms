"""
AI-Powered Payment Prediction Service

Predicts customer payment behavior:
- When invoices will be paid
- Payment delay probability
- Collection priority ranking
- Cash flow forecasting

Uses customer payment history and behavioral patterns.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.billing import TaxInvoice as Invoice, InvoiceStatus, PaymentReceipt


class PaymentPredictionService:
    """
    AI service for predicting payment behavior and optimizing collections.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Customer Payment Profile ====================

    async def _get_customer_payment_history(
        self,
        customer_id: UUID
    ) -> Dict:
        """
        Build a customer's payment history profile.
        """
        # Get all paid invoices for this customer
        query = select(
            Invoice.id,
            Invoice.invoice_date,
            Invoice.due_date,
            Invoice.total_amount,
            Invoice.status,
            PaymentReceipt.receipt_date,
            PaymentReceipt.amount
        ).outerjoin(
            Receipt, PaymentReceipt.invoice_id == Invoice.id
        ).where(
            Invoice.customer_id == customer_id
        ).order_by(
            Invoice.invoice_date.desc()
        )

        result = await self.db.execute(query)
        rows = result.all()

        if not rows:
            return {
                "total_invoices": 0,
                "paid_invoices": 0,
                "avg_payment_days": 0,
                "late_payment_ratio": 0,
                "avg_delay_days": 0,
                "payment_consistency": 0.5,  # Default neutral
                "total_value": 0
            }

        total_invoices = 0
        paid_invoices = 0
        payment_delays = []
        total_value = Decimal('0')
        late_payments = 0

        invoice_payments = defaultdict(list)
        for row in rows:
            invoice_payments[row.id].append(row)

        for invoice_id, payments in invoice_payments.items():
            first_payment = payments[0]
            total_invoices += 1
            total_value += first_payment.total_amount or Decimal('0')

            if first_payment.receipt_date:
                paid_invoices += 1

                # Calculate days to payment
                invoice_date = first_payment.invoice_date
                payment_date = first_payment.receipt_date
                due_date = first_payment.due_date

                if isinstance(invoice_date, datetime):
                    invoice_date = invoice_date.date()
                if isinstance(payment_date, datetime):
                    payment_date = payment_date.date()
                if isinstance(due_date, datetime):
                    due_date = due_date.date()

                days_to_pay = (payment_date - invoice_date).days
                payment_delays.append(days_to_pay)

                # Check if late
                if due_date and payment_date > due_date:
                    late_payments += 1

        avg_payment_days = sum(payment_delays) / len(payment_delays) if payment_delays else 30
        late_ratio = late_payments / paid_invoices if paid_invoices > 0 else 0.5

        # Calculate payment consistency (lower variance = more consistent)
        if len(payment_delays) >= 2:
            mean = avg_payment_days
            variance = sum((x - mean) ** 2 for x in payment_delays) / len(payment_delays)
            std_dev = variance ** 0.5
            consistency = max(0, 1 - (std_dev / 30))  # Normalize to 0-1
        else:
            consistency = 0.5

        return {
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
            "avg_payment_days": round(avg_payment_days, 1),
            "late_payment_ratio": round(late_ratio, 2),
            "avg_delay_days": round(avg_payment_days - 30, 1) if avg_payment_days > 30 else 0,
            "payment_consistency": round(consistency, 2),
            "total_value": float(total_value)
        }

    # ==================== Invoice Payment Prediction ====================

    async def predict_invoice_payment(
        self,
        invoice_id: UUID
    ) -> Dict:
        """
        Predict when a specific invoice will be paid.
        """
        # Get invoice details
        invoice_query = select(Invoice).options(
            joinedload(Invoice.customer)
        ).where(Invoice.id == invoice_id)

        result = await self.db.execute(invoice_query)
        invoice = result.unique().scalar_one_or_none()

        if not invoice:
            return {"error": "Invoice not found"}

        # Get customer payment history
        history = await self._get_customer_payment_history(invoice.customer_id)

        # Calculate prediction factors
        invoice_date = invoice.invoice_date
        due_date = invoice.due_date
        amount = float(invoice.total_amount or 0)

        if isinstance(invoice_date, datetime):
            invoice_date = invoice_date.date()
        if isinstance(due_date, datetime):
            due_date = due_date.date()

        # Base prediction: avg payment days from history
        base_prediction_days = history["avg_payment_days"] if history["avg_payment_days"] > 0 else 30

        # Adjust for invoice amount (larger invoices may take longer)
        avg_value = history["total_value"] / history["total_invoices"] if history["total_invoices"] > 0 else amount
        if amount > avg_value * 1.5:
            base_prediction_days += 5  # Large invoice adjustment
        elif amount < avg_value * 0.5:
            base_prediction_days -= 3  # Small invoice adjustment

        # Adjust for day of week (payments often on Monday/Friday)
        predicted_date = invoice_date + timedelta(days=int(base_prediction_days))
        if predicted_date.weekday() in [5, 6]:  # Saturday/Sunday
            predicted_date += timedelta(days=(7 - predicted_date.weekday()))

        # Calculate delay probability
        delay_probability = self._calculate_delay_probability(
            history,
            amount,
            (due_date - invoice_date).days if due_date else 30
        )

        # Determine risk category
        if delay_probability >= 0.7:
            risk_category = "HIGH"
            recommended_action = "Immediate follow-up required"
        elif delay_probability >= 0.4:
            risk_category = "MEDIUM"
            recommended_action = "Send payment reminder before due date"
        else:
            risk_category = "LOW"
            recommended_action = "Standard follow-up process"

        # Calculate confidence based on history
        if history["total_invoices"] >= 10:
            confidence = 0.85
        elif history["total_invoices"] >= 5:
            confidence = 0.70
        elif history["total_invoices"] >= 2:
            confidence = 0.55
        else:
            confidence = 0.40

        # Factors affecting prediction
        factors = []
        if history["late_payment_ratio"] > 0.5:
            factors.append({
                "factor": "Payment History",
                "impact": "negative",
                "detail": f"{int(history['late_payment_ratio']*100)}% invoices paid late"
            })
        else:
            factors.append({
                "factor": "Payment History",
                "impact": "positive",
                "detail": f"Good payment track record"
            })

        if amount > avg_value * 1.5:
            factors.append({
                "factor": "Invoice Amount",
                "impact": "negative",
                "detail": f"50%+ higher than customer's average"
            })
        elif amount < avg_value * 0.5:
            factors.append({
                "factor": "Invoice Amount",
                "impact": "positive",
                "detail": "Below average, likely quick payment"
            })
        else:
            factors.append({
                "factor": "Invoice Amount",
                "impact": "neutral",
                "detail": "Within usual range"
            })

        factors.append({
            "factor": "Payment Consistency",
            "impact": "positive" if history["payment_consistency"] > 0.6 else "neutral",
            "detail": f"Consistency score: {history['payment_consistency']}"
        })

        return {
            "invoice_id": str(invoice_id),
            "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer.name if invoice.customer else "Unknown",
            "amount_due": amount,
            "invoice_date": invoice_date.isoformat(),
            "due_date": due_date.isoformat() if due_date else None,

            "predicted_payment_date": predicted_date.isoformat(),
            "predicted_days_to_payment": (predicted_date - invoice_date).days,
            "delay_probability": round(delay_probability, 2),
            "delay_days_predicted": max(0, (predicted_date - due_date).days) if due_date else 0,

            "risk_category": risk_category,
            "recommended_action": recommended_action,
            "confidence_score": confidence,

            "factors": factors,

            "customer_profile": {
                "avg_payment_days": history["avg_payment_days"],
                "late_payment_ratio": history["late_payment_ratio"],
                "total_invoices": history["total_invoices"]
            }
        }

    def _calculate_delay_probability(
        self,
        history: Dict,
        amount: float,
        credit_days: int
    ) -> float:
        """
        Calculate probability of payment delay.
        """
        # Base probability from historical late ratio
        base_prob = history["late_payment_ratio"]

        # Adjust for amount
        avg_amount = history["total_value"] / history["total_invoices"] if history["total_invoices"] > 0 else amount
        if amount > avg_amount * 2:
            base_prob += 0.15
        elif amount > avg_amount * 1.5:
            base_prob += 0.08

        # Adjust for credit terms
        if credit_days < 15:
            base_prob += 0.10  # Short credit = higher delay chance
        elif credit_days > 45:
            base_prob -= 0.05  # Longer credit = lower delay

        # Adjust for consistency
        base_prob -= (history["payment_consistency"] - 0.5) * 0.2

        # New customer adjustment
        if history["total_invoices"] < 3:
            base_prob = max(base_prob, 0.4)  # Minimum risk for new customers

        return max(0, min(1, base_prob))

    # ==================== Collection Priority ====================

    async def get_collection_priority_list(
        self,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get prioritized list of invoices for collection.
        """
        # Get all unpaid/pending invoices
        query = select(Invoice).options(
            joinedload(Invoice.customer)
        ).where(
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.SENT])
        ).order_by(
            Invoice.due_date.asc()
        )

        result = await self.db.execute(query)
        invoices = result.unique().scalars().all()

        priority_list = []
        for invoice in invoices:
            # Get prediction for each invoice
            prediction = await self.predict_invoice_payment(invoice.id)
            if "error" in prediction:
                continue

            # Calculate priority score (0-100)
            # Factors: Amount, Days overdue, Risk category, Customer value

            due_date = invoice.due_date
            if isinstance(due_date, datetime):
                due_date = due_date.date()

            days_overdue = (date.today() - due_date).days if due_date else 0

            # Score components
            overdue_score = min(40, max(0, days_overdue * 2))  # Max 40 points
            amount_score = min(30, float(invoice.total_amount or 0) / 10000 * 30)  # Max 30 points
            risk_score = {"HIGH": 30, "MEDIUM": 15, "LOW": 5}.get(prediction["risk_category"], 10)

            total_score = overdue_score + amount_score + risk_score

            priority_list.append({
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_id": str(invoice.customer_id),
                "customer_name": invoice.customer.name if invoice.customer else "Unknown",
                "customer_phone": invoice.customer.phone if invoice.customer else None,
                "customer_email": invoice.customer.email if invoice.customer else None,

                "amount_due": float(invoice.total_amount or 0),
                "due_date": due_date.isoformat() if due_date else None,
                "days_overdue": max(0, days_overdue),

                "predicted_payment_date": prediction["predicted_payment_date"],
                "delay_probability": prediction["delay_probability"],
                "risk_category": prediction["risk_category"],

                "priority_score": round(total_score, 1),
                "recommended_action": self._get_collection_action(days_overdue, prediction["risk_category"]),

                "collection_status": "OVERDUE" if days_overdue > 0 else "UPCOMING"
            })

        # Sort by priority score (highest first)
        priority_list.sort(key=lambda x: x["priority_score"], reverse=True)

        return priority_list[:limit]

    def _get_collection_action(self, days_overdue: int, risk_category: str) -> str:
        """Get recommended collection action."""
        if days_overdue > 30:
            return "ESCALATE_TO_MANAGEMENT"
        elif days_overdue > 14:
            return "PHONE_CALL_FOLLOWUP"
        elif days_overdue > 7:
            return "SEND_REMINDER_EMAIL"
        elif days_overdue > 0:
            return "AUTOMATED_REMINDER"
        elif risk_category == "HIGH":
            return "PROACTIVE_CALL"
        else:
            return "STANDARD_PROCESS"

    # ==================== Cash Flow Prediction ====================

    async def predict_cash_flow(
        self,
        days_ahead: int = 30
    ) -> Dict:
        """
        Predict cash flow based on pending invoices.
        """
        # Get all pending invoices
        query = select(Invoice).where(
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.SENT])
        )

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Group predicted collections by day
        daily_predictions = defaultdict(lambda: {"expected": 0, "pessimistic": 0, "optimistic": 0})

        for invoice in invoices:
            try:
                prediction = await self.predict_invoice_payment(invoice.id)
                if "error" in prediction:
                    continue

                pred_date = datetime.fromisoformat(prediction["predicted_payment_date"]).date()
                amount = prediction["amount_due"]
                delay_prob = prediction["delay_probability"]

                # Only include predictions within forecast window
                if pred_date <= date.today() + timedelta(days=days_ahead):
                    # Expected = amount * (1 - delay_probability)
                    daily_predictions[pred_date]["expected"] += amount * (1 - delay_prob)

                    # Optimistic = full amount
                    daily_predictions[pred_date]["optimistic"] += amount

                    # Pessimistic = amount * (1 - delay_prob) * 0.7
                    daily_predictions[pred_date]["pessimistic"] += amount * (1 - delay_prob) * 0.7
            except Exception:
                continue

        # Build forecast
        forecast = []
        total_expected = 0
        total_pessimistic = 0
        total_optimistic = 0

        current = date.today()
        for i in range(days_ahead):
            current_date = current + timedelta(days=i+1)
            day_data = daily_predictions.get(current_date, {"expected": 0, "pessimistic": 0, "optimistic": 0})

            total_expected += day_data["expected"]
            total_pessimistic += day_data["pessimistic"]
            total_optimistic += day_data["optimistic"]

            forecast.append({
                "date": current_date.isoformat(),
                "expected": round(day_data["expected"], 2),
                "cumulative_expected": round(total_expected, 2),
                "optimistic": round(day_data["optimistic"], 2),
                "pessimistic": round(day_data["pessimistic"], 2)
            })

        # Weekly summary
        weekly_summary = []
        for week in range(min(4, days_ahead // 7 + 1)):
            week_start = week * 7
            week_end = min((week + 1) * 7, len(forecast))
            week_data = forecast[week_start:week_end]

            weekly_summary.append({
                "week": week + 1,
                "expected": round(sum(d["expected"] for d in week_data), 2),
                "optimistic": round(sum(d["optimistic"] for d in week_data), 2),
                "pessimistic": round(sum(d["pessimistic"] for d in week_data), 2)
            })

        return {
            "generated_at": datetime.now().isoformat(),
            "forecast_days": days_ahead,
            "pending_invoices": len(invoices),

            "totals": {
                "expected_collection": round(total_expected, 2),
                "optimistic_collection": round(total_optimistic, 2),
                "pessimistic_collection": round(total_pessimistic, 2)
            },

            "daily_forecast": forecast,
            "weekly_summary": weekly_summary,

            "insights": [
                f"Expected collections: ₹{total_expected:,.2f}",
                f"Collection range: ₹{total_pessimistic:,.2f} - ₹{total_optimistic:,.2f}",
                f"Based on {len(invoices)} pending invoices"
            ]
        }

    # ==================== Customer Credit Scoring ====================

    async def get_customer_credit_score(
        self,
        customer_id: UUID
    ) -> Dict:
        """
        Calculate credit score for a customer.
        """
        history = await self._get_customer_payment_history(customer_id)

        # Get customer details
        customer_query = select(Customer).where(Customer.id == customer_id)
        result = await self.db.execute(customer_query)
        customer = result.scalar_one_or_none()

        if not customer:
            return {"error": "Customer not found"}

        # Calculate score components (0-100 scale)

        # 1. Payment timeliness (40 points max)
        timeliness_score = 40 * (1 - history["late_payment_ratio"])

        # 2. Payment consistency (20 points max)
        consistency_score = 20 * history["payment_consistency"]

        # 3. Transaction volume (20 points max)
        volume_score = min(20, history["total_invoices"] * 2)

        # 4. Total value (20 points max)
        value_score = min(20, history["total_value"] / 50000 * 20)

        total_score = timeliness_score + consistency_score + volume_score + value_score

        # Determine grade
        if total_score >= 80:
            grade = "A"
            recommendation = "Extend credit terms, priority customer"
        elif total_score >= 60:
            grade = "B"
            recommendation = "Standard credit terms apply"
        elif total_score >= 40:
            grade = "C"
            recommendation = "Reduced credit limit, closer monitoring"
        else:
            grade = "D"
            recommendation = "Cash on delivery preferred"

        return {
            "customer_id": str(customer_id),
            "customer_name": customer.name,

            "credit_score": round(total_score, 1),
            "grade": grade,
            "recommendation": recommendation,

            "score_breakdown": {
                "payment_timeliness": round(timeliness_score, 1),
                "payment_consistency": round(consistency_score, 1),
                "transaction_volume": round(volume_score, 1),
                "total_value": round(value_score, 1)
            },

            "payment_profile": {
                "total_invoices": history["total_invoices"],
                "late_payment_ratio": history["late_payment_ratio"],
                "avg_payment_days": history["avg_payment_days"],
                "total_value": history["total_value"]
            }
        }
