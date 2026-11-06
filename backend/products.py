from pydantic import BaseModel
from typing import Dict, Optional, List

class ProductConfig(BaseModel):
    product_id: str
    name: str
    description: str
    base_url: str
    login_path: str = "/login"
    home_path: str = "/dashboard/Intake/Manual%20Case%20Registration"
    default_credentials: Dict[str, str] = {
        "username": "srihari.banda",
        "password": "Clinevo@2026",
        "enterprise": "Clinevo"
    }

PRODUCT_REGISTRY: Dict[str, ProductConfig] = {
    "onepv": ProductConfig(
        product_id="onepv",
        name="Clinevo OnePV (Dev)",
        description="Clinevo OnePV Enterprise Safety and Adverse Event Intake",
        base_url="https://dev.one-aipv.com",
        login_path="/login",
        home_path="/dashboard/Intake/Manual%20Case%20Registration"
    ),
    "signal": ProductConfig(
        product_id="signal",
        name="Clinevo Signal",
        description="Pharmacovigilance Signal Management, Disproportionality, and Risk Assessment",
        base_url="https://signal.clinevo.com",
        login_path="/login",
        home_path="/signal/dashboard"
    ),
    "onepv_mock": ProductConfig(
        product_id="onepv_mock",
        name="Clinevo OnePV (Mock Vercel)",
        description="Mock OnePV Sandbox for offline and demo qualification",
        base_url="https://mpv-two.vercel.app",
        login_path="/login",
        home_path="/intake/manual-case-registration"
    ),
    "custom": ProductConfig(
        product_id="custom",
        name="Custom Target",
        description="Configure custom web application or enterprise safety portal URL",
        base_url="",
        login_path="/login",
        home_path="/"
    )
}

def get_product(product_id: str) -> ProductConfig:
    p_id = (product_id or "onepv").lower().strip()
    return PRODUCT_REGISTRY.get(p_id, PRODUCT_REGISTRY["onepv"])

def list_products() -> List[ProductConfig]:
    return list(PRODUCT_REGISTRY.values())
