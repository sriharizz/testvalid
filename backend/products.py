from pydantic import BaseModel
from typing import Dict, Optional, List

class ProductConfig(BaseModel):
    product_id: str
    name: str
    description: str
    base_url: str
    login_path: str = "/login"
    home_path: str = "/intake/manual-case-registration"
    default_credentials: Dict[str, str] = {
        "username": "sirihari.banda",
        "password": "Clinevo@2026",
        "enterprise": "Clinevo"
    }

PRODUCT_REGISTRY: Dict[str, ProductConfig] = {
    "onepv": ProductConfig(
        product_id="onepv",
        name="Clinevo OnePV",
        description="Pharmacovigilance Intake, Case Registration, and Triage portal",
        base_url="https://mpv-two.vercel.app",
        login_path="/login",
        home_path="/intake/manual-case-registration"
    ),
    "signal": ProductConfig(
        product_id="signal",
        name="Clinevo Signal",
        description="Pharmacovigilance Signal Management, Disproportionality, and Risk Assessment",
        base_url="https://signal.clinevo.com",
        login_path="/login",
        home_path="/signal/dashboard"
    ),
    "1pv": ProductConfig(
        product_id="1pv",
        name="1PV Enterprise Core",
        description="Enterprise Safety Database and Regulatory Reporting",
        base_url="https://app.1pv.com",
        login_path="/auth",
        home_path="/cases"
    )
}

def get_product(product_id: str) -> ProductConfig:
    p_id = (product_id or "onepv").lower().strip()
    return PRODUCT_REGISTRY.get(p_id, PRODUCT_REGISTRY["onepv"])

def list_products() -> List[ProductConfig]:
    return list(PRODUCT_REGISTRY.values())

def register_custom_product(product_id: str, name: str, base_url: str, description: str = "") -> ProductConfig:
    cfg = ProductConfig(
        product_id=product_id.lower().strip(),
        name=name,
        description=description or f"Custom portal at {base_url}",
        base_url=base_url.rstrip("/")
    )
    PRODUCT_REGISTRY[cfg.product_id] = cfg
    return cfg
