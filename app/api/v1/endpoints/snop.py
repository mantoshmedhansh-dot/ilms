"""
S&OP (Sales and Operations Planning) API Endpoints

Comprehensive demand forecasting and supply planning:
- Demand Forecasting (multi-level, ensemble AI)
- Supply Planning
- Inventory Optimization
- Scenario Analysis
- Consensus Planning
- Approval Workflow
"""

from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import TenantDB, CurrentUser
from app.models.snop import (
    ForecastGranularity,
    ForecastLevel,
    ForecastStatus,
    ForecastAlgorithm,
    SupplyPlanStatus,
    ScenarioStatus,
    ExternalFactorType,
    DemandSignalType,
    DemandSignalStatus,
)
from app.schemas.snop import (
    DemandForecastCreate,
    DemandForecastGenerateRequest,
    DemandForecastResponse,
    DemandForecastBrief,
    ForecastAdjustmentCreate,
    ForecastAdjustmentResponse,
    ForecastApprovalRequest,
    SupplyPlanCreate,
    SupplyPlanOptimizeRequest,
    SupplyPlanResponse,
    SNOPScenarioCreate,
    SNOPScenarioRunRequest,
    SNOPScenarioResponse,
    ScenarioCompareRequest,
    ScenarioCompareResponse,
    ExternalFactorCreate,
    ExternalFactorResponse,
    InventoryOptimizationRequest,
    InventoryOptimizationResponse,
    ApplyOptimizationRequest,
    SNOPMeetingCreate,
    SNOPMeetingUpdate,
    SNOPMeetingResponse,
    SNOPDashboardSummary,
    ForecastAccuracyReport,
    DemandSupplyGapAnalysis,
    DemandSignalCreate,
    DemandSignalUpdate,
    DemandSignalResponse,
    DemandSensingAnalysis,
    SupplyOptimizeAdvancedRequest,
    MultiSourceRequest,
    MonteCarloRequest,
    FinancialPLRequest,
    SensitivityRequest,
    QuickWhatIfRequest,
    ScenarioCompareAdvancedRequest,
)
from app.services.snop import SNOPService, DemandPlannerService, MLForecaster, DemandClassifier, DemandSensor, SupplyOptimizer, ScenarioEngine, PlanningAgents, NLPlanner
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=SNOPDashboardSummary)
@require_module("scm_ai")
async def get_snop_dashboard(
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Get S&OP dashboard summary.

    Includes:
    - Forecast counts and accuracy
    - Demand vs Supply gap
    - Inventory health indicators
    - Upcoming S&OP meetings
    """
    snop_service = SNOPService(db)
    return await snop_service.get_dashboard_summary()


@router.get("/dashboard/demand-supply-gap", response_model=DemandSupplyGapAnalysis)
@require_module("scm_ai")
async def get_demand_supply_gap(
    db: TenantDB,
    current_user: CurrentUser,
    horizon_days: int = Query(90, ge=7, le=365, description="Forecast horizon in days")
):
    """
    Get demand vs supply gap analysis.
    """
    snop_service = SNOPService(db)
    return await snop_service.get_demand_supply_gap(horizon_days)


@router.get("/dashboard/forecast-accuracy", response_model=ForecastAccuracyReport)
@require_module("scm_ai")
async def get_forecast_accuracy_report(
    db: TenantDB,
    current_user: CurrentUser,
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date")
):
    """
    Get forecast accuracy report for the specified period.
    """
    snop_service = SNOPService(db)
    return await snop_service.get_forecast_accuracy_report(start_date, end_date)


# ==================== Demand Forecasting ====================

@router.post("/forecast/generate")
@require_module("scm_ai")
async def generate_forecasts(
    request: DemandForecastGenerateRequest,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Generate AI-powered demand forecasts.

    Supports:
    - Multiple products/categories at once
    - Multiple forecast levels (SKU, Category, Region)
    - Multiple granularities (Daily, Weekly, Monthly)
    - Ensemble AI algorithms
    """
    snop_service = SNOPService(db)

    from datetime import date as date_type
    forecast_start = request.forecast_start_date or date_type.today()

    forecasts = await snop_service.generate_forecasts(
        product_ids=request.product_ids,
        category_ids=request.category_ids,
        warehouse_ids=request.warehouse_ids,
        forecast_level=request.forecast_level,
        granularity=request.granularity,
        forecast_start_date=forecast_start,
        forecast_horizon_days=request.forecast_horizon_days,
        algorithm=request.algorithm,
        lookback_days=request.lookback_days,
        user_id=current_user.id
    )

    return {
        "message": f"Generated {len(forecasts)} forecasts",
        "forecast_ids": [str(f.id) for f in forecasts],
        "forecasts": [
            {
                "id": str(f.id),
                "code": f.forecast_code,
                "name": f.forecast_name,
                "level": f.forecast_level,
                "algorithm": f.algorithm_used,
                "total_qty": float(f.total_forecasted_qty),
                "mape": f.mape
            }
            for f in forecasts
        ]
    }


@router.post("/forecast/compare-models")
@require_module("scm_ai")
async def compare_forecast_models(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    granularity: ForecastGranularity = Query(ForecastGranularity.WEEKLY),
    lookback_days: int = Query(365, ge=90, le=1095),
    forecast_horizon_days: int = Query(30, ge=7, le=365),
):
    """
    Compare all ML forecasting models for a product/category.

    Returns accuracy metrics for each model (Prophet, XGBoost, ARIMA, Holt-Winters, Ensemble)
    along with the auto-selected best model and demand classification (ABC-XYZ).
    """
    ml_forecaster = MLForecaster(db)

    periods = forecast_horizon_days if granularity == ForecastGranularity.DAILY else (forecast_horizon_days // 7)

    result = await ml_forecaster.auto_forecast(
        product_id=product_id,
        category_id=category_id,
        lookback_days=lookback_days,
        forecast_periods=max(1, periods),
        granularity=granularity,
    )

    return {
        "winning_model": result["accuracy_metrics"].get("winning_model", "ensemble"),
        "winning_mape": result["accuracy_metrics"].get("mape", 100),
        "model_comparison": result["accuracy_metrics"].get("model_comparison", {}),
        "demand_classification": result.get("demand_classification", {}),
        "forecast_data": result["forecasts"],
        "data_points": result.get("data_points", 0),
        "ml_libraries": {
            "prophet": ml_forecaster.has_prophet,
            "xgboost": ml_forecaster.has_xgboost,
            "statsmodels": ml_forecaster.has_statsmodels,
            "sklearn": ml_forecaster.has_sklearn,
        },
    }


@router.get("/demand-classification")
@require_module("scm_ai")
async def get_demand_classification(
    db: TenantDB,
    current_user: CurrentUser,
    lookback_days: int = Query(365, ge=90, le=1095),
    granularity: ForecastGranularity = Query(ForecastGranularity.WEEKLY),
):
    """
    Classify all products using ABC-XYZ demand analysis.

    Returns each product's classification, coefficient of variation,
    and recommended forecasting algorithm.
    """
    from app.models.product import Product

    demand_planner = DemandPlannerService(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    # Get all active products
    result = await db.execute(
        select(Product).where(Product.is_active == True).limit(200)
    )
    products = list(result.scalars().all())

    classifications = []
    for product in products:
        historical = await demand_planner.get_historical_demand(
            product_id=product.id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )

        data = [float(h["quantity"]) for h in historical] if historical else []
        classification = DemandClassifier.classify_demand(data)

        classifications.append({
            "product_id": str(product.id),
            "product_name": product.name,
            "sku": getattr(product, 'sku', None),
            "abc_class": classification["abc_class"],
            "xyz_class": classification["xyz_class"],
            "combined_class": classification["combined_class"],
            "cv": classification["cv"],
            "mean_demand": classification.get("mean_demand", 0),
            "recommended_algorithm": classification["recommended_algorithm"].value,
            "data_points": len(data),
        })

    # Sort by ABC class (A first) then by CV
    classifications.sort(key=lambda x: (x["abc_class"], x["cv"]))

    return {
        "total_products": len(classifications),
        "summary": {
            "A": len([c for c in classifications if c["abc_class"] == "A"]),
            "B": len([c for c in classifications if c["abc_class"] == "B"]),
            "C": len([c for c in classifications if c["abc_class"] == "C"]),
            "X": len([c for c in classifications if c["xyz_class"] == "X"]),
            "Y": len([c for c in classifications if c["xyz_class"] == "Y"]),
            "Z": len([c for c in classifications if c["xyz_class"] == "Z"]),
        },
        "classifications": classifications,
    }


@router.get("/forecasts")
@require_module("scm_ai")
async def list_forecasts(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    status: Optional[ForecastStatus] = Query(None),
    forecast_level: Optional[ForecastLevel] = Query(None),
    level: Optional[ForecastLevel] = Query(None),
    granularity: Optional[ForecastGranularity] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List demand forecasts with filters.

    Accepts both 'level' and 'forecast_level' params (frontend sends 'level').
    Returns 'items' array with computed 'accuracy' (100 - mape) and 'avg_accuracy'.
    """
    from app.models.snop import DemandForecast
    from sqlalchemy.orm import selectinload
    from sqlalchemy import func as sa_func

    # Accept both 'level' and 'forecast_level' params
    effective_level = forecast_level or level

    query = select(DemandForecast).where(DemandForecast.is_active == True)
    count_query = select(sa_func.count(DemandForecast.id)).where(DemandForecast.is_active == True)

    if product_id:
        query = query.where(DemandForecast.product_id == product_id)
        count_query = count_query.where(DemandForecast.product_id == product_id)
    if category_id:
        query = query.where(DemandForecast.category_id == category_id)
        count_query = count_query.where(DemandForecast.category_id == category_id)
    if status:
        query = query.where(DemandForecast.status == status.value)
        count_query = count_query.where(DemandForecast.status == status.value)
    if effective_level:
        query = query.where(DemandForecast.forecast_level == effective_level.value)
        count_query = count_query.where(DemandForecast.forecast_level == effective_level.value)
    if granularity:
        query = query.where(DemandForecast.granularity == granularity.value)
        count_query = count_query.where(DemandForecast.granularity == granularity.value)

    # Eager load product/category relationships for display names
    query = query.options(
        selectinload(DemandForecast.product),
        selectinload(DemandForecast.category),
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DemandForecast.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    forecasts = list(result.scalars().all())

    items = []
    mape_values = []
    for f in forecasts:
        mape_val = float(f.mape) if f.mape is not None else None
        accuracy = round(max(0, 100 - mape_val), 1) if mape_val is not None else None
        if mape_val is not None:
            mape_values.append(mape_val)

        items.append({
            "id": str(f.id),
            "code": f.forecast_code,
            "name": f.forecast_name,
            "product_name": f.product.name if f.product else None,
            "category_name": f.category.name if f.category else None,
            "level": f.forecast_level,
            "granularity": f.granularity,
            "start_date": f.forecast_start_date.isoformat(),
            "end_date": f.forecast_end_date.isoformat(),
            "total_qty": float(f.total_forecasted_qty),
            "algorithm": f.algorithm_used,
            "mape": mape_val,
            "accuracy": accuracy,
            "status": f.status,
            "created_at": f.created_at.isoformat(),
        })

    avg_accuracy = round(100 - (sum(mape_values) / len(mape_values)), 1) if mape_values else None

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "avg_accuracy": avg_accuracy,
        "items": items,
    }


@router.get("/forecast/{forecast_id}")
@require_module("scm_ai")
async def get_forecast(
    forecast_id: UUID,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Get detailed forecast information.
    """
    demand_planner = DemandPlannerService(db)
    forecast = await demand_planner.get_forecast(forecast_id)

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast {forecast_id} not found"
        )

    return {
        "id": str(forecast.id),
        "code": forecast.forecast_code,
        "name": forecast.forecast_name,
        "level": forecast.forecast_level,
        "granularity": forecast.granularity,
        "product_id": str(forecast.product_id) if forecast.product_id else None,
        "product_name": forecast.product.name if forecast.product else None,
        "category_id": str(forecast.category_id) if forecast.category_id else None,
        "category_name": forecast.category.name if forecast.category else None,
        "warehouse_id": str(forecast.warehouse_id) if forecast.warehouse_id else None,
        "warehouse_name": forecast.warehouse.name if forecast.warehouse else None,
        "channel": forecast.channel,
        "forecast_start_date": forecast.forecast_start_date.isoformat(),
        "forecast_end_date": forecast.forecast_end_date.isoformat(),
        "horizon_days": forecast.forecast_horizon_days,
        "forecast_data": forecast.forecast_data,
        "total_forecasted_qty": float(forecast.total_forecasted_qty),
        "avg_daily_demand": float(forecast.avg_daily_demand),
        "peak_demand": float(forecast.peak_demand),
        "algorithm": forecast.algorithm_used,
        "model_parameters": forecast.model_parameters,
        "accuracy_metrics": {
            "mape": forecast.mape,
            "mae": forecast.mae,
            "rmse": forecast.rmse,
            "bias": forecast.forecast_bias
        },
        "confidence_level": forecast.confidence_level,
        "status": forecast.status,
        "version": forecast.version,
        "created_at": forecast.created_at.isoformat(),
        "submitted_at": forecast.submitted_at.isoformat() if forecast.submitted_at else None,
        "approved_at": forecast.approved_at.isoformat() if forecast.approved_at else None,
        "notes": forecast.notes,
        "adjustments": [
            {
                "id": str(adj.id),
                "date": adj.adjustment_date.isoformat(),
                "original_qty": float(adj.original_qty),
                "adjusted_qty": float(adj.adjusted_qty),
                "adjustment_pct": adj.adjustment_pct,
                "reason": adj.adjustment_reason,
                "status": adj.status
            }
            for adj in forecast.adjustments
        ] if forecast.adjustments else []
    }


# ==================== Forecast Workflow ====================

@router.post("/forecast/{forecast_id}/submit")
@require_module("scm_ai")
async def submit_forecast_for_review(
    forecast_id: UUID,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Submit a forecast for review and approval.
    """
    demand_planner = DemandPlannerService(db)

    try:
        forecast = await demand_planner.submit_for_review(forecast_id, current_user.id)
        return {
            "message": "Forecast submitted for review",
            "forecast_id": str(forecast.id),
            "status": forecast.status
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forecast/{forecast_id}/approve")
@require_module("scm_ai")
async def approve_forecast(
    forecast_id: UUID,
    request: ForecastApprovalRequest,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Approve, reject, or request changes to a forecast.
    """
    demand_planner = DemandPlannerService(db)

    try:
        if request.action == "approve":
            forecast = await demand_planner.approve_forecast(forecast_id, current_user.id, request.comments)
        elif request.action == "reject":
            forecast = await demand_planner.reject_forecast(forecast_id, current_user.id, request.comments or "Rejected")
        else:  # request_changes
            forecast = await demand_planner.request_adjustment(forecast_id, current_user.id, request.comments or "Please review")

        result = {
            "message": f"Forecast {request.action}d successfully",
            "forecast_id": str(forecast.id),
            "status": forecast.status,
        }

        # Auto-generate supply plan on approval
        if request.action == "approve" and request.auto_generate_supply_plan:
            try:
                supply_optimizer = SupplyOptimizer(db)
                supply_plan_result = await supply_optimizer.optimize_supply(
                    forecast_id=forecast_id,
                    user_id=current_user.id,
                )
                result["supply_plan"] = {
                    "plan_id": supply_plan_result.get("plan_id") or supply_plan_result.get("id"),
                    "message": "Supply plan auto-generated from approved forecast",
                    "details": supply_plan_result,
                }
            except Exception as e:
                import logging
                logging.warning(f"Auto supply plan generation failed for forecast {forecast_id}: {e}")
                result["supply_plan_error"] = str(e)

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Forecast Adjustments ====================

@router.post("/forecast/{forecast_id}/adjust")
@require_module("scm_ai")
async def create_forecast_adjustment(
    forecast_id: UUID,
    request: ForecastAdjustmentCreate,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Create a manual adjustment to a forecast.
    """
    demand_planner = DemandPlannerService(db)

    try:
        adjustment = await demand_planner.create_adjustment(
            forecast_id=forecast_id,
            adjustment_date=request.adjustment_date,
            adjusted_qty=request.adjusted_qty,
            adjustment_reason=request.adjustment_reason,
            user_id=current_user.id,
            justification=request.justification
        )

        return {
            "message": "Adjustment created and pending approval",
            "adjustment_id": str(adjustment.id),
            "original_qty": float(adjustment.original_qty),
            "adjusted_qty": float(adjustment.adjusted_qty),
            "adjustment_pct": adjustment.adjustment_pct
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/adjustment/{adjustment_id}/approve")
@require_module("scm_ai")
async def approve_adjustment(
    adjustment_id: UUID,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Approve a forecast adjustment.
    """
    demand_planner = DemandPlannerService(db)

    try:
        adjustment = await demand_planner.approve_adjustment(adjustment_id, current_user.id)
        return {
            "message": "Adjustment approved and applied to forecast",
            "adjustment_id": str(adjustment.id),
            "status": adjustment.status
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Supply Planning ====================

@router.get("/supply-plans")
@require_module("scm_ai")
async def list_supply_plans(
    db: TenantDB,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List supply plans with summary stats.

    Returns 'items' array. Each item includes a computed 'plan_type'
    (PRODUCTION or PROCUREMENT) based on which quantity is larger.
    """
    from app.models.snop import SupplyPlan
    from sqlalchemy import func as sa_func

    query = select(SupplyPlan)
    count_query = select(sa_func.count(SupplyPlan.id))

    if status:
        query = query.where(SupplyPlan.status == status)
        count_query = count_query.where(SupplyPlan.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(SupplyPlan.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    plans = list(result.scalars().all())

    items = []
    for p in plans:
        prod_qty = float(p.planned_production_qty or 0)
        proc_qty = float(p.planned_procurement_qty or 0)
        plan_type = "PRODUCTION" if prod_qty >= proc_qty else "PROCUREMENT"

        items.append({
            "id": str(p.id),
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "plan_type": plan_type,
            "start_date": p.plan_start_date.isoformat(),
            "end_date": p.plan_end_date.isoformat(),
            "total_quantity": prod_qty + proc_qty,
            "planned_production_qty": prod_qty,
            "planned_procurement_qty": proc_qty,
            "capacity_utilization": float(p.capacity_utilization_pct or 0),
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        })

    return {"items": items, "total": total}


@router.post("/supply-plan", response_model=SupplyPlanResponse)
@require_module("scm_ai")
async def create_supply_plan(
    request: SupplyPlanCreate,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Create a new supply plan.
    """
    snop_service = SNOPService(db)

    plan = await snop_service.create_supply_plan(
        plan_name=request.plan_name,
        forecast_id=request.forecast_id,
        plan_start_date=request.plan_start_date,
        plan_end_date=request.plan_end_date,
        product_id=request.product_id,
        warehouse_id=request.warehouse_id,
        vendor_id=request.vendor_id,
        user_id=current_user.id,
        notes=request.notes
    )

    return {
        "id": plan.id,
        "plan_code": plan.plan_code,
        "plan_name": plan.plan_name,
        "forecast_id": plan.forecast_id,
        "plan_start_date": plan.plan_start_date,
        "plan_end_date": plan.plan_end_date,
        "product_id": plan.product_id,
        "warehouse_id": plan.warehouse_id,
        "vendor_id": plan.vendor_id,
        "planned_production_qty": plan.planned_production_qty,
        "planned_procurement_qty": plan.planned_procurement_qty,
        "production_capacity": plan.production_capacity,
        "capacity_utilization_pct": plan.capacity_utilization_pct,
        "lead_time_days": plan.lead_time_days,
        "schedule_data": plan.schedule_data,
        "status": plan.status,
        "created_at": plan.created_at,
        "notes": plan.notes
    }


@router.post("/supply-plan/optimize")
@require_module("scm_ai")
async def optimize_supply_plan(
    request: SupplyPlanOptimizeRequest,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Create an AI-optimized supply plan based on a forecast.
    """
    snop_service = SNOPService(db)

    try:
        plan = await snop_service.optimize_supply_plan(
            forecast_id=request.forecast_id,
            target_service_level=request.target_service_level,
            max_capacity_utilization=request.max_capacity_utilization,
            min_safety_stock_days=request.min_safety_stock_days,
            user_id=current_user.id
        )

        return {
            "message": "Optimized supply plan created",
            "plan_id": str(plan.id),
            "plan_code": plan.plan_code,
            "planned_production": float(plan.planned_production_qty),
            "planned_procurement": float(plan.planned_procurement_qty),
            "status": plan.status
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/supply-plan/optimize-advanced")
@require_module("scm_ai")
async def optimize_supply_advanced(
    request: SupplyOptimizeAdvancedRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Run constraint-based supply optimization.

    Uses linear programming (scipy) when available, with fallback to heuristic solver.
    Constraints: capacity, budget, MOQ, lead time, service level target.
    Minimizes total cost (production + procurement + holding + stockout penalty).
    """
    optimizer = SupplyOptimizer(db)

    try:
        result = await optimizer.optimize_supply(
            forecast_id=request.forecast_id,
            constraints={
                "max_production_capacity": request.max_production_capacity,
                "max_budget": request.max_budget,
                "min_order_qty": request.min_order_qty,
                "max_lead_time_days": request.max_lead_time_days,
                "target_service_level": request.target_service_level,
                "holding_cost_per_unit": request.holding_cost_per_unit,
                "stockout_penalty_per_unit": request.stockout_penalty_per_unit,
                "production_cost_per_unit": request.production_cost_per_unit,
                "procurement_cost_per_unit": request.procurement_cost_per_unit,
            },
            user_id=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/supply-plan/capacity-analysis")
@require_module("scm_ai")
async def get_capacity_analysis(
    db: TenantDB,
    current_user: CurrentUser,
    forecast_id: Optional[UUID] = Query(None),
    horizon_days: int = Query(90, ge=7, le=365),
    daily_capacity: float = Query(1000, ge=1),
):
    """
    Analyze production capacity utilization against demand.

    Returns capacity timeline, bottleneck detection, and recommendations.
    """
    optimizer = SupplyOptimizer(db)

    return await optimizer.analyze_capacity(
        forecast_id=forecast_id,
        horizon_days=horizon_days,
        daily_capacity=daily_capacity,
    )


@router.get("/supply-plan/ddmrp-buffers")
@require_module("scm_ai")
async def get_ddmrp_buffers(
    db: TenantDB,
    current_user: CurrentUser,
    lookback_days: int = Query(90, ge=30, le=365),
):
    """
    Calculate DDMRP buffer zones for all products.

    Returns Red/Yellow/Green zones, net flow position, and action needed indicators.
    """
    optimizer = SupplyOptimizer(db)

    return await optimizer.calculate_ddmrp_buffers(lookback_days=lookback_days)


@router.post("/supply-plan/multi-source")
@require_module("scm_ai")
async def analyze_multi_source(
    request: MultiSourceRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Analyze and score multiple vendors for procurement.

    Scoring: Cost (40%), Lead Time (25%), Reliability (20%), MOQ Flexibility (15%).
    """
    optimizer = SupplyOptimizer(db)

    return await optimizer.multi_source_analysis(
        product_id=request.product_id,
        required_qty=request.required_qty,
        max_lead_time_days=request.max_lead_time_days,
    )


# ==================== Inventory Optimization ====================

@router.get("/inventory/optimizations")
@require_module("scm_ai")
async def list_inventory_optimizations(
    db: TenantDB,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List inventory optimization recommendations.

    Returns 'items' array with product details, current stock, and
    recommended safety stock / reorder point / EOQ per product-warehouse.
    """
    from app.models.snop import InventoryOptimization
    from app.models.product import Product
    from app.models.warehouse import Warehouse
    from app.models.inventory import InventorySummary
    from sqlalchemy import func as sa_func, and_

    count_query = select(sa_func.count(InventoryOptimization.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(InventoryOptimization)
        .order_by(InventoryOptimization.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    optimizations = list(result.scalars().all())

    if not optimizations:
        return {"items": [], "total": total, "potential_savings": 0}

    # Batch fetch product and warehouse names
    product_ids = list({o.product_id for o in optimizations})
    warehouse_ids = list({o.warehouse_id for o in optimizations})

    prod_result = await db.execute(
        select(Product.id, Product.name, Product.sku).where(Product.id.in_(product_ids))
    )
    product_map = {str(r[0]): {"name": r[1], "sku": r[2]} for r in prod_result.all()}

    wh_result = await db.execute(
        select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))
    )
    warehouse_map = {str(r[0]): r[1] for r in wh_result.all()}

    # Batch fetch current stock levels
    stock_map = {}
    for o in optimizations:
        inv_result = await db.execute(
            select(sa_func.coalesce(sa_func.sum(InventorySummary.available_quantity), 0))
            .where(
                and_(
                    InventorySummary.product_id == o.product_id,
                    InventorySummary.warehouse_id == o.warehouse_id,
                )
            )
        )
        stock_map[(str(o.product_id), str(o.warehouse_id))] = float(inv_result.scalar() or 0)

    items = []
    potential_savings = 0.0
    for o in optimizations:
        pid_str = str(o.product_id)
        wid_str = str(o.warehouse_id)
        prod_info = product_map.get(pid_str, {"name": "Unknown", "sku": None})
        wh_name = warehouse_map.get(wid_str, "Unknown")
        current_stock = stock_map.get((pid_str, wid_str), 0)

        rec_safety = float(o.recommended_safety_stock)
        rec_reorder = float(o.recommended_reorder_point)
        rec_eoq = float(o.recommended_order_qty)

        items.append({
            "id": str(o.id),
            "product_name": prod_info["name"],
            "sku": prod_info["sku"],
            "warehouse_name": wh_name,
            "current_stock": current_stock,
            "recommended_safety_stock": rec_safety,
            "recommended_reorder_point": rec_reorder,
            "recommended_eoq": rec_eoq,
            "current_safety_stock": float(o.current_safety_stock),
            "expected_stockout_rate": float(o.expected_stockout_rate),
            "expected_inventory_turns": float(o.expected_inventory_turns),
            "is_applied": o.is_applied,
        })

        # Estimate savings from excess stock
        if current_stock > rec_reorder * 1.5:
            excess = current_stock - rec_reorder
            potential_savings += excess * float(o.holding_cost_pct) * 100

    return {
        "items": items,
        "total": total,
        "potential_savings": round(potential_savings, 0),
    }


@router.post("/inventory/optimize")
@require_module("scm_ai")
async def calculate_inventory_optimization(
    request: InventoryOptimizationRequest,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Calculate inventory optimization recommendations.

    Calculates:
    - Optimal safety stock levels
    - Reorder points
    - Economic order quantities
    """
    snop_service = SNOPService(db)
    results = []

    # For each product-warehouse combination
    product_ids = request.product_ids or []
    warehouse_ids = request.warehouse_ids or []

    # Auto-populate with all active products/warehouses if not specified
    if not product_ids:
        from app.models.product import Product
        result = await db.execute(
            select(Product.id).where(Product.is_active == True)
        )
        product_ids = [row[0] for row in result.fetchall()]
    if not warehouse_ids:
        from app.models.warehouse import Warehouse
        result = await db.execute(
            select(Warehouse.id).where(Warehouse.is_active == True)
        )
        warehouse_ids = [row[0] for row in result.fetchall()]

    if not product_ids or not warehouse_ids:
        return {
            "message": "No active products or warehouses found",
            "optimizations": []
        }

    for product_id in product_ids:
        for warehouse_id in warehouse_ids:
            try:
                optimization = await snop_service.create_inventory_optimization(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    service_level_target=request.service_level_target,
                    lead_time_days=14,  # Would come from vendor data
                    holding_cost_pct=request.holding_cost_pct,
                    ordering_cost=request.ordering_cost,
                    valid_days=90
                )

                results.append({
                    "id": str(optimization.id),
                    "product_id": str(optimization.product_id),
                    "warehouse_id": str(optimization.warehouse_id),
                    "recommended_safety_stock": float(optimization.recommended_safety_stock),
                    "recommended_reorder_point": float(optimization.recommended_reorder_point),
                    "recommended_order_qty": float(optimization.recommended_order_qty),
                    "current_safety_stock": float(optimization.current_safety_stock),
                    "expected_stockout_rate": optimization.expected_stockout_rate,
                    "expected_inventory_turns": optimization.expected_inventory_turns
                })
            except Exception as e:
                results.append({
                    "product_id": str(product_id),
                    "warehouse_id": str(warehouse_id),
                    "error": str(e)
                })

    return {
        "message": f"Generated {len(results)} optimization recommendations",
        "optimizations": results
    }


@router.get("/inventory/safety-stock/{product_id}/{warehouse_id}")
@require_module("scm_ai")
async def get_safety_stock_recommendation(
    product_id: UUID,
    warehouse_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
    service_level: float = Query(0.95, ge=0.8, le=0.99),
    lead_time_days: int = Query(14, ge=1)
):
    """
    Get safety stock recommendation for a product-warehouse combination.
    """
    snop_service = SNOPService(db)

    result = await snop_service.calculate_safety_stock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        service_level=service_level,
        lead_time_days=lead_time_days
    )

    return result


# ==================== Scenario Analysis ====================

@router.get("/scenarios")
@require_module("scm_ai")
async def list_scenarios(
    db: TenantDB,
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List S&OP scenarios.

    Returns 'items' array with scenario details and simulation results.
    """
    from app.models.snop import SNOPScenario
    from sqlalchemy import func as sa_func

    query = select(SNOPScenario).where(SNOPScenario.is_active == True)
    count_query = select(sa_func.count(SNOPScenario.id)).where(SNOPScenario.is_active == True)

    if status:
        query = query.where(SNOPScenario.status == status)
        count_query = count_query.where(SNOPScenario.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(SNOPScenario.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    scenarios = list(result.scalars().all())

    items = []
    for s in scenarios:
        items.append({
            "id": str(s.id),
            "scenario_code": s.scenario_code,
            "name": s.scenario_name,
            "scenario_name": s.scenario_name,
            "description": s.description,
            "status": s.status,
            "results": s.results,
            "simulation_start_date": s.simulation_start_date.isoformat(),
            "simulation_end_date": s.simulation_end_date.isoformat(),
            "created_at": s.created_at.isoformat(),
        })

    return {"items": items, "total": total}


@router.post("/scenario", response_model=SNOPScenarioResponse)
@require_module("scm_ai")
async def create_scenario(
    request: SNOPScenarioCreate,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Create a what-if scenario for analysis.
    """
    snop_service = SNOPService(db)

    scenario = await snop_service.create_scenario(
        scenario_name=request.scenario_name,
        simulation_start_date=request.simulation_start_date,
        simulation_end_date=request.simulation_end_date,
        assumptions=request.assumptions.model_dump(),
        base_scenario_id=request.base_scenario_id,
        description=request.description,
        user_id=current_user.id
    )

    return {
        "id": scenario.id,
        "scenario_code": scenario.scenario_code,
        "scenario_name": scenario.scenario_name,
        "description": scenario.description,
        "simulation_start_date": scenario.simulation_start_date,
        "simulation_end_date": scenario.simulation_end_date,
        "assumptions": request.assumptions,
        "status": scenario.status,
        "created_at": scenario.created_at
    }


@router.post("/scenario/{scenario_id}/run")
@require_module("scm_ai")
async def run_scenario_simulation(
    scenario_id: UUID,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Run simulation for a scenario.
    """
    snop_service = SNOPService(db)

    try:
        scenario = await snop_service.run_scenario_simulation(scenario_id)

        return {
            "message": "Scenario simulation completed",
            "scenario_id": str(scenario.id),
            "status": scenario.status,
            "results": scenario.results
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/scenarios/compare")
@require_module("scm_ai")
async def compare_scenarios(
    request: ScenarioCompareRequest,
    db: TenantDB,
    current_user: CurrentUser
):
    """
    Compare multiple scenarios side by side.
    """
    from sqlalchemy import select
    from app.models.snop import SNOPScenario

    result = await db.execute(
        select(SNOPScenario)
        .where(SNOPScenario.id.in_(request.scenario_ids))
    )
    scenarios = list(result.scalars().all())

    if len(scenarios) != len(request.scenario_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more scenarios not found"
        )

    comparison = {}
    for metric in request.comparison_metrics:
        comparison[metric] = {}
        for scenario in scenarios:
            if scenario.results:
                comparison[metric][scenario.scenario_name] = scenario.results.get(f"projected_{metric}", "N/A")

    # Determine recommendation
    recommendation = None
    if all(s.results for s in scenarios):
        best_revenue = max(scenarios, key=lambda s: s.results.get("projected_revenue", 0))
        recommendation = f"Scenario '{best_revenue.scenario_name}' shows highest projected revenue"

    return {
        "scenarios": [
            {
                "id": str(s.id),
                "name": s.scenario_name,
                "status": s.status,
                "results": s.results
            }
            for s in scenarios
        ],
        "comparison_table": comparison,
        "recommendation": recommendation
    }


# ==================== Advanced Scenario Engine ====================

@router.post("/scenario/monte-carlo")
@require_module("scm_ai")
async def run_monte_carlo_simulation(
    request: MonteCarloRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Run Monte Carlo simulation for a scenario.

    Performs N random simulations varying demand, supply, lead time, and price
    using statistical distributions. Returns percentile-based confidence intervals,
    revenue distribution histogram, and risk metrics.
    """
    engine = ScenarioEngine(db)

    try:
        result = await engine.run_monte_carlo(
            scenario_id=request.scenario_id,
            num_simulations=request.num_simulations,
            demand_cv=request.demand_cv,
            supply_cv=request.supply_cv,
            lead_time_cv=request.lead_time_cv,
            price_cv=request.price_cv,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/scenario/financial-pl")
@require_module("scm_ai")
async def project_financial_pl(
    request: FinancialPLRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Generate financial P&L projection for a scenario.

    Returns monthly breakdown with Revenue, COGS, Gross Margin,
    Operating Expenses, EBITDA, Tax, Net Income, and waterfall chart data.
    """
    engine = ScenarioEngine(db)

    try:
        result = await engine.project_financial_pl(
            scenario_id=request.scenario_id,
            avg_unit_price=request.avg_unit_price,
            cogs_pct=request.cogs_pct,
            operating_expense_pct=request.operating_expense_pct,
            tax_rate_pct=request.tax_rate_pct,
            working_capital_days=request.working_capital_days,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/scenario/sensitivity")
@require_module("scm_ai")
async def run_sensitivity_analysis(
    request: SensitivityRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Run sensitivity analysis for tornado chart visualization.

    Varies each parameter independently by +/- variation_pct while holding
    all others constant. Shows which parameters have the biggest impact on
    revenue and net income.
    """
    engine = ScenarioEngine(db)

    try:
        result = await engine.sensitivity_analysis(
            scenario_id=request.scenario_id,
            parameters=request.parameters,
            variation_pct=request.variation_pct,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/scenario/what-if")
@require_module("scm_ai")
async def quick_what_if_analysis(
    request: QuickWhatIfRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Quick what-if analysis without creating a scenario record.

    Instantly shows the financial impact of parameter changes
    (demand, price, supply, lead time, COGS) on a 90-day projection.
    """
    engine = ScenarioEngine(db)

    return await engine.quick_what_if(
        demand_change_pct=request.demand_change_pct,
        price_change_pct=request.price_change_pct,
        supply_change_pct=request.supply_change_pct,
        lead_time_change_pct=request.lead_time_change_pct,
        cogs_change_pct=request.cogs_change_pct,
    )


@router.post("/scenarios/compare-advanced")
@require_module("scm_ai")
async def compare_scenarios_advanced(
    request: ScenarioCompareAdvancedRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Advanced scenario comparison with weighted scoring and ranking.

    Ranks scenarios across: Revenue (30%), Net Income (25%),
    Service Level (20%), Risk Score (15%), Efficiency (10%).
    Custom weights can be provided.
    """
    engine = ScenarioEngine(db)

    try:
        return await engine.compare_scenarios_advanced(
            scenario_ids=request.scenario_ids,
            ranking_weights=request.ranking_weights,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Historical Data ====================

@router.get("/historical/demand")
@require_module("scm_ai")
async def get_historical_demand(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    start_date: date = Query(...),
    end_date: date = Query(...),
    granularity: ForecastGranularity = Query(ForecastGranularity.DAILY)
):
    """
    Get historical demand data.
    """
    demand_planner = DemandPlannerService(db)

    data = await demand_planner.get_historical_demand(
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity
    )

    return {
        "product_id": str(product_id) if product_id else None,
        "category_id": str(category_id) if category_id else None,
        "warehouse_id": str(warehouse_id) if warehouse_id else None,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "granularity": granularity.value,
        "data_points": len(data),
        "data": [
            {
                "date": d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"]),
                "quantity": float(d["quantity"]),
                "revenue": float(d["revenue"])
            }
            for d in data
        ]
    }


@router.get("/historical/demand/by-product")
@require_module("scm_ai")
async def get_demand_by_product(
    db: TenantDB,
    current_user: CurrentUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
    warehouse_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    top_n: int = Query(50, ge=1, le=200)
):
    """
    Get demand aggregated by product.
    """
    demand_planner = DemandPlannerService(db)

    data = await demand_planner.get_demand_by_product(
        start_date=start_date,
        end_date=end_date,
        warehouse_id=warehouse_id,
        category_id=category_id,
        top_n=top_n
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_products": len(data),
        "products": [
            {
                "product_id": str(d["product_id"]),
                "product_name": d["product_name"],
                "product_sku": d["product_sku"],
                "total_quantity": float(d["total_quantity"]),
                "total_revenue": float(d["total_revenue"]),
                "order_count": d["order_count"]
            }
            for d in data
        ]
    }


@router.get("/historical/demand/by-channel")
@require_module("scm_ai")
async def get_demand_by_channel(
    db: TenantDB,
    current_user: CurrentUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
    product_id: Optional[UUID] = Query(None)
):
    """
    Get demand aggregated by sales channel.
    """
    demand_planner = DemandPlannerService(db)

    data = await demand_planner.get_demand_by_channel(
        start_date=start_date,
        end_date=end_date,
        product_id=product_id
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "channels": data
    }


@router.get("/historical/statistics")
@require_module("scm_ai")
async def get_demand_statistics(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    lookback_days: int = Query(365, ge=30, le=1095)
):
    """
    Get demand statistics for inventory optimization.
    """
    demand_planner = DemandPlannerService(db)

    stats = await demand_planner.calculate_demand_statistics(
        product_id=product_id,
        category_id=category_id,
        warehouse_id=warehouse_id,
        lookback_days=lookback_days
    )

    return stats


# ==================== Demand Sensing ====================

@router.post("/demand-signals")
@require_module("scm_ai")
async def create_demand_signal(
    request: DemandSignalCreate,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Create a new demand signal.

    Signals represent real-time demand indicators from various sources:
    POS data, promotions, weather, market intelligence, social media, etc.
    """
    sensor = DemandSensor(db)

    signal = await sensor.create_signal(
        signal_name=request.signal_name,
        signal_type=request.signal_type,
        effective_start=request.effective_start,
        effective_end=request.effective_end,
        impact_direction=request.impact_direction,
        impact_pct=request.impact_pct,
        signal_strength=request.signal_strength,
        confidence=request.confidence,
        decay_rate=request.decay_rate,
        product_id=request.product_id,
        category_id=request.category_id,
        region_id=request.region_id,
        channel=request.channel,
        applies_to_all=request.applies_to_all,
        source=request.source,
        source_data=request.source_data,
        user_id=current_user.id,
        notes=request.notes,
    )

    info = sensor.compute_signal_info(signal)

    return {
        "message": "Demand signal created",
        "signal": {
            "id": str(signal.id),
            "code": signal.signal_code,
            "name": signal.signal_name,
            "type": signal.signal_type,
            "strength": signal.signal_strength,
            "current_strength": info["current_strength"],
            "impact_direction": signal.impact_direction,
            "impact_pct": signal.impact_pct,
            "effective_start": signal.effective_start.isoformat(),
            "effective_end": signal.effective_end.isoformat(),
            "status": signal.status,
        },
    }


@router.get("/demand-signals")
@require_module("scm_ai")
async def list_demand_signals(
    db: TenantDB,
    current_user: CurrentUser,
    status: Optional[DemandSignalStatus] = Query(None),
    signal_type: Optional[DemandSignalType] = Query(None),
    product_id: Optional[UUID] = Query(None),
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List demand signals with filters.
    """
    sensor = DemandSensor(db)

    signals, total = await sensor.list_signals(
        status=status,
        signal_type=signal_type,
        product_id=product_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "signals": [
            {
                "id": str(s.id),
                "code": s.signal_code,
                "name": s.signal_name,
                "type": s.signal_type,
                "product_id": str(s.product_id) if s.product_id else None,
                "category_id": str(s.category_id) if s.category_id else None,
                "channel": s.channel,
                "applies_to_all": s.applies_to_all,
                "strength": s.signal_strength,
                "current_strength": sensor.compute_signal_info(s)["current_strength"],
                "impact_direction": s.impact_direction,
                "impact_pct": s.impact_pct,
                "confidence": s.confidence,
                "detected_at": s.detected_at.isoformat() if s.detected_at else None,
                "effective_start": s.effective_start.isoformat(),
                "effective_end": s.effective_end.isoformat(),
                "days_active": sensor.compute_signal_info(s)["days_active"],
                "days_remaining": sensor.compute_signal_info(s)["days_remaining"],
                "decay_rate": s.decay_rate,
                "source": s.source,
                "status": s.status,
                "actual_impact": s.actual_impact,
                "created_at": s.created_at.isoformat(),
                "notes": s.notes,
            }
            for s in signals
        ],
    }


@router.put("/demand-signals/{signal_id}")
@require_module("scm_ai")
async def update_demand_signal(
    signal_id: UUID,
    request: DemandSignalUpdate,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Update a demand signal.
    """
    sensor = DemandSensor(db)

    signal = await sensor.update_signal(
        signal_id=signal_id,
        signal_strength=request.signal_strength,
        impact_pct=request.impact_pct,
        confidence=request.confidence,
        effective_end=request.effective_end,
        status=request.status,
        actual_impact=request.actual_impact,
        notes=request.notes,
        user_id=current_user.id,
    )

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demand signal {signal_id} not found",
        )

    return {
        "message": "Demand signal updated",
        "signal_id": str(signal.id),
        "status": signal.status,
    }


@router.post("/demand-signals/{signal_id}/dismiss")
@require_module("scm_ai")
async def dismiss_demand_signal(
    signal_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Dismiss a demand signal as irrelevant.
    """
    sensor = DemandSensor(db)
    signal = await sensor.dismiss_signal(signal_id, current_user.id)

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demand signal {signal_id} not found",
        )

    return {"message": "Signal dismissed", "signal_id": str(signal.id)}


@router.post("/demand-signals/analyze")
@require_module("scm_ai")
async def analyze_demand_signals(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    horizon_days: int = Query(30, ge=7, le=180),
):
    """
    Run demand sensing analysis.

    Aggregates all active signals, computes net forecast adjustment,
    and generates actionable recommendations.
    """
    sensor = DemandSensor(db)

    analysis = await sensor.analyze_demand_signals(
        product_id=product_id,
        category_id=category_id,
        horizon_days=horizon_days,
    )

    return analysis


@router.post("/demand-signals/apply-to-forecast/{forecast_id}")
@require_module("scm_ai")
async def apply_signals_to_forecast(
    forecast_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Apply active demand signals to adjust a forecast.

    This modifies the forecast data points based on the net signal impact.
    """
    sensor = DemandSensor(db)

    try:
        result = await sensor.apply_signals_to_forecast(forecast_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/demand-signals/detect-pos")
@require_module("scm_ai")
async def detect_pos_signals(
    db: TenantDB,
    current_user: CurrentUser,
    lookback_days: int = Query(7, ge=3, le=30),
    spike_threshold: float = Query(1.5, ge=1.1, le=3.0),
    drop_threshold: float = Query(0.5, ge=0.1, le=0.9),
):
    """
    Auto-detect demand signals from recent POS/order data.

    Compares recent daily demand to historical average and creates
    signals when thresholds are exceeded.
    """
    sensor = DemandSensor(db)

    signals = await sensor.detect_pos_signals(
        lookback_days=lookback_days,
        spike_threshold=spike_threshold,
        drop_threshold=drop_threshold,
    )

    return {
        "message": f"Detected {len(signals)} POS signals",
        "signals": [
            {
                "id": str(s.id),
                "code": s.signal_code,
                "name": s.signal_name,
                "type": s.signal_type,
                "product_id": str(s.product_id) if s.product_id else None,
                "impact_direction": s.impact_direction,
                "impact_pct": s.impact_pct,
                "strength": s.signal_strength,
                "source_data": s.source_data,
            }
            for s in signals
        ],
    }


# ==================== AI Planning Agents ====================

@router.get("/agents/status")
@require_module("scm_ai")
async def get_agents_status(
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Get status of all AI planning agents.

    Returns each agent's readiness, data sources, and capabilities.
    """
    agents = PlanningAgents(db)
    return await agents.get_agent_status()


@router.get("/agents/alert-center")
@require_module("scm_ai")
async def get_alert_center(
    db: TenantDB,
    current_user: CurrentUser,
    include_exceptions: bool = Query(True),
    include_reorder: bool = Query(True),
    include_bias: bool = Query(True),
    max_alerts: int = Query(50, ge=1, le=200),
):
    """
    Get aggregated alert center from all AI agents.

    Runs all active agents and returns prioritized, deduplicated alerts
    with severity scoring and recommended actions.
    """
    agents = PlanningAgents(db)

    return await agents.get_alert_center(
        include_exceptions=include_exceptions,
        include_reorder=include_reorder,
        include_bias=include_bias,
        max_alerts=max_alerts,
    )


@router.post("/agents/run-exceptions")
@require_module("scm_ai")
async def run_exception_agent(
    db: TenantDB,
    current_user: CurrentUser,
    safety_stock_threshold: float = Query(1.0, ge=0.5, le=2.0),
    overstock_days: int = Query(90, ge=30, le=365),
    gap_pct_threshold: float = Query(10.0, ge=1, le=50),
):
    """
    Run the Exception Detection Agent.

    Scans for stockout risks, overstock situations, and demand-supply gaps.
    """
    agents = PlanningAgents(db)

    return await agents.run_exception_agent(
        safety_stock_threshold=safety_stock_threshold,
        overstock_days_threshold=overstock_days,
        gap_pct_threshold=gap_pct_threshold,
    )


@router.post("/agents/run-reorder")
@require_module("scm_ai")
async def run_reorder_agent(
    db: TenantDB,
    current_user: CurrentUser,
    lead_time_buffer_pct: float = Query(20.0, ge=0, le=100),
):
    """
    Run the Reorder Agent.

    Auto-generates purchase order suggestions for products below reorder point.
    """
    agents = PlanningAgents(db)

    return await agents.run_reorder_agent(
        lead_time_buffer_pct=lead_time_buffer_pct,
    )


@router.post("/agents/run-bias")
@require_module("scm_ai")
async def run_bias_agent(
    db: TenantDB,
    current_user: CurrentUser,
    bias_threshold_pct: float = Query(10.0, ge=1, le=50),
):
    """
    Run the Forecast Bias Agent.

    Analyzes forecast accuracy to detect systematic bias, compare algorithms,
    and suggest corrections.
    """
    agents = PlanningAgents(db)

    return await agents.run_bias_agent(
        bias_threshold_pct=bias_threshold_pct,
    )


# ==================== Reorder -> Purchase Requisition ====================

class ConvertSuggestionRequest(BaseModel):
    """Request to convert a reorder suggestion to PR."""
    suggestion: dict = Field(..., description="Reorder suggestion dict from run_reorder_agent")


@router.post("/agents/reorder-suggestion/convert-to-pr")
@require_module("scm_ai")
async def convert_suggestion_to_pr(
    request: ConvertSuggestionRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Convert a reorder agent suggestion into a DRAFT Purchase Requisition.
    """
    agents = PlanningAgents(db)
    return await agents.create_purchase_requisition_from_suggestion(
        suggestion=request.suggestion,
        user_id=current_user.id,
    )


class SupplyPlanApproveRequest(BaseModel):
    """Request to approve a supply plan."""
    auto_create_pr: bool = Field(True, description="Auto-create Purchase Requisition if procurement qty > 0")


@router.post("/supply-plan/{plan_id}/approve")
@require_module("scm_ai")
async def approve_supply_plan(
    plan_id: UUID,
    request: SupplyPlanApproveRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Approve a supply plan and optionally auto-create Purchase Requisition.
    """
    service = SNOPService(db)
    return await service.approve_supply_plan(
        plan_id=plan_id,
        approved_by=current_user.id,
        auto_create_pr=request.auto_create_pr,
    )


# ==================== Natural Language Planning ====================

class ChatRequest(BaseModel):
    """Natural language chat request."""
    query: str = Field(..., min_length=1, max_length=500)


@router.post("/chat")
@require_module("scm_ai")
async def chat_with_planner(
    request: ChatRequest,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Natural language S&OP planning assistant.

    Accepts conversational queries and returns structured responses
    with data, narrative, suggested follow-ups, and quick actions.

    Examples:
    - "What's the demand forecast for next quarter?"
    - "Show me stockout risks"
    - "Compare our scenarios"
    - "Any alerts from the AI agents?"
    """
    planner = NLPlanner(db)

    return await planner.process_query(
        query=request.query,
        user_id=current_user.id,
    )
