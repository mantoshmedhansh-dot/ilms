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

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import DB, CurrentUser
from app.models.snop import (
    ForecastGranularity,
    ForecastLevel,
    ForecastStatus,
    ForecastAlgorithm,
    SupplyPlanStatus,
    ScenarioStatus,
    ExternalFactorType,
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
)
from app.services.snop import SNOPService, DemandPlannerService, MLForecaster, DemandClassifier
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=SNOPDashboardSummary)
@require_module("scm_ai")
async def get_snop_dashboard(
    db: DB,
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
    db: DB,
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
    db: DB,
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
    db: DB,
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

    forecasts = await snop_service.generate_forecasts(
        product_ids=request.product_ids,
        category_ids=request.category_ids,
        warehouse_ids=request.warehouse_ids,
        forecast_level=request.forecast_level,
        granularity=request.granularity,
        forecast_start_date=request.forecast_start_date,
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
    db: DB,
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
    db: DB,
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
    db: DB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    status: Optional[ForecastStatus] = Query(None),
    forecast_level: Optional[ForecastLevel] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List demand forecasts with filters.
    """
    demand_planner = DemandPlannerService(db)

    forecasts, total = await demand_planner.list_forecasts(
        product_id=product_id,
        category_id=category_id,
        status=status,
        forecast_level=forecast_level,
        limit=limit,
        offset=offset
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "forecasts": [
            {
                "id": str(f.id),
                "code": f.forecast_code,
                "name": f.forecast_name,
                "level": f.forecast_level,
                "granularity": f.granularity,
                "start_date": f.forecast_start_date.isoformat(),
                "end_date": f.forecast_end_date.isoformat(),
                "total_qty": float(f.total_forecasted_qty),
                "algorithm": f.algorithm_used,
                "mape": f.mape,
                "status": f.status,
                "created_at": f.created_at.isoformat()
            }
            for f in forecasts
        ]
    }


@router.get("/forecast/{forecast_id}")
@require_module("scm_ai")
async def get_forecast(
    forecast_id: UUID,
    db: DB,
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
    db: DB,
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
    db: DB,
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

        return {
            "message": f"Forecast {request.action}d successfully",
            "forecast_id": str(forecast.id),
            "status": forecast.status
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Forecast Adjustments ====================

@router.post("/forecast/{forecast_id}/adjust")
@require_module("scm_ai")
async def create_forecast_adjustment(
    forecast_id: UUID,
    request: ForecastAdjustmentCreate,
    db: DB,
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
    db: DB,
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

@router.post("/supply-plan", response_model=SupplyPlanResponse)
@require_module("scm_ai")
async def create_supply_plan(
    request: SupplyPlanCreate,
    db: DB,
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
    db: DB,
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


# ==================== Inventory Optimization ====================

@router.post("/inventory/optimize")
@require_module("scm_ai")
async def calculate_inventory_optimization(
    request: InventoryOptimizationRequest,
    db: DB,
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

    if not product_ids or not warehouse_ids:
        return {
            "message": "Please specify at least one product and warehouse",
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
    db: DB,
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

@router.post("/scenario", response_model=SNOPScenarioResponse)
@require_module("scm_ai")
async def create_scenario(
    request: SNOPScenarioCreate,
    db: DB,
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
    db: DB,
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
    db: DB,
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


# ==================== Historical Data ====================

@router.get("/historical/demand")
@require_module("scm_ai")
async def get_historical_demand(
    db: DB,
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
    db: DB,
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
    db: DB,
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
    db: DB,
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
