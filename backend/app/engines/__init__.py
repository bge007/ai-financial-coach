from app.engines.profile import compute_profile
from app.engines.budget import fifty_thirty_twenty
from app.engines.investment import risk_allocation, project_growth
from app.engines.tax_india import compare_regimes, sip_maturity, epf_projection, nps_projection
from app.engines.debt import payoff_schedule

__all__ = [
    "compute_profile",
    "fifty_thirty_twenty",
    "risk_allocation",
    "project_growth",
    "compare_regimes",
    "sip_maturity",
    "epf_projection",
    "nps_projection",
    "payoff_schedule",
]
