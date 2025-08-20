from fastapi import FastAPI
from pydantic import BaseModel
from datetime import date

app = FastAPI(title="Nutrition Coach API")

ACT_MULT = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "athlete": 1.9,
}

class ProfileIn(BaseModel):
    sex: str                  # "male" / "female"
    birth_date: date          # פורמט YYYY-MM-DD
    height_cm: float
    weight_kg: float
    activity_level: str       # אחד מהמפתחות ב-ACT_MULT
    weekly_loss_kg: float = 0.25   # קצב ירידה רצוי (ק"ג לשבוע)
    macro_pref: str = "balanced"   # "balanced" או "high_protein"

def _age(d: date) -> int:
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

def _bmr_msj(sex: str, weight: float, height: float, age: int) -> float:
    if sex.lower() == "male":
        return 10*weight + 6.25*height - 5*age + 5
    return 10*weight + 6.25*height - 5*age - 161

def _tdee(profile: ProfileIn) -> float:
    return _bmr_msj(profile.sex, profile.weight_kg, profile.height_cm, _age(profile.birth_date)) * ACT_MULT[profile.activity_level]

def _deficit_per_day(weekly_loss_kg: float) -> float:
    # ~7700 קק"ל לק"ג
    return min(900, max(250, weekly_loss_kg * 7700 / 7))

def _macro_split(kcal: float, pref: str):
    if pref == "high_protein":
        p, c, f = 0.30, 0.40, 0.30
    else:
        p, c, f = 0.25, 0.45, 0.30
    return round((kcal*p)/4), round((kcal*c)/4), round((kcal*f)/9)

@app.get("/")
def root():
    return {"ok": True}

@app.post("/targets")
def compute_targets(p: ProfileIn):
    base = _tdee(p)
    kcal = base - _deficit_per_day(p.weekly_loss_kg)

    # guardrails פשוטים
    min_kcal = 1500 if p.sex.lower() == "male" else 1200
    warnings = []
    if kcal < min_kcal:
        warnings.append(f"יעד נמוך מהמינימום המומלץ ({min_kcal} קק\"ל). כיוונתי למינימום.")
        kcal = min_kcal

    protein_g, carbs_g, fat_g = _macro_split(kcal, p.macro_pref)
    return {
        "targets": {
            "kcal": round(kcal),
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g
        },
        "tdee": round(base),
        "warnings": warnings
    }
