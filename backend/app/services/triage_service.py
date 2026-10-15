import re
from dataclasses import dataclass, field
from typing import Iterable


EMERGENCY_CONTACTS = {
    "default": ["112", "108"],
    "mental_health": ["Tele-MANAS 14416", "112"],
}


@dataclass
class TriageResult:
    urgency: str
    category: str
    summary: str
    guidance: str
    emergency_numbers: list[str] = field(default_factory=list)
    safety_block: bool = False
    flags: list[str] = field(default_factory=list)
    is_medical_guidance_only: bool = True

    def to_reply(self) -> str:
        prefix = "Emergency guidance: " if self.urgency == "emergency" else "Safety guidance: "
        contacts = ", ".join(self.emergency_numbers) if self.emergency_numbers else "contact a local emergency service"
        return (
            f"{prefix}{self.summary} {self.guidance} "
            f"Call {contacts}. This is not a medical diagnosis. Please seek urgent professional advice."
        )


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _self_harm_patterns() -> tuple[str, ...]:
    return (
        "want to die",
        "suicidal",
        "self-harm",
        "hurt myself",
        "end my life",
        "kill myself",
        "suicide",
        "khudkushi",
        "aatmahatya",
        "apni jaan lena",
        "khud ko nuksan",
        "khud ko maar",
        "marna chahta",
        "marna chahti",
        "jeena nahi chahta",
        "jeena nahi chahti",
        "आत्महत्या",
        "खुदकुशी",
        "खुद को नुकसान",
        "मरना चाहता",
        "मरना चाहती",
    )


def _prompt_injection_patterns() -> tuple[str, ...]:
    return (
        "ignore all previous instructions",
        "system prompt",
        "override the rules",
        "developer message",
        "ignore the system",
        "do not follow these instructions",
    )


def _obvious_red_flags(text: str) -> list[str]:
    lower = _normalise_text(text)
    flags: list[str] = []
    if _contains_any(lower, [
        "chest pain", "pressure in chest", "tight chest", "squeezing chest",
        "seene mein dard", "seene me dard", "chhati mein dard", "chhati me dard",
        "सीने में दर्द", "छाती में दर्द",
    ]):
        flags.append("chest_pain")
    if _contains_any(lower, [
        "breathlessness", "shortness of breath", "trouble breathing", "difficulty breathing",
        "can't breathe", "cant breathe", "gasping", "saans nahi aa rahi", "saans nahin aa rahi",
        "saans lene mein dikkat", "saans lene me dikkat", "saans lene mein takleef",
        "saans lene me takleef", "सांस नहीं आ रही", "साँस नहीं आ रही",
        "सांस लेने में दिक्कत", "साँस लेने में दिक्कत",
    ]):
        flags.append("breathing")
    if _contains_any(lower, [
        "face drooping", "one side of face", "slurred speech", "weak arm",
        "can't smile", "cannot smile", "stroke", "chehra tedha", "bolne mein dikkat",
        "एक तरफ चेहरा", "चेहरा टेढ़ा", "बोलने में दिक्कत",
    ]):
        flags.append("stroke")
    if _contains_any(lower, [
        "severe bleeding", "bleeding heavily", "lots of blood", "blood loss",
        "bleeding won't stop", "bleeding is heavy", "bahut khoon beh",
        "khoon ruk nahi raha", "बहुत खून बह", "खून रुक नहीं रहा",
    ]):
        flags.append("severe_bleeding")
    if _contains_any(lower, ["seizure", "fit", "convulsion", "uncontrolled shaking", "daura pad", "दौरा पड़"]):
        flags.append("seizure")
    if _contains_any(lower, [
        "passed out", "unconscious", "loss of consciousness", "fainted", "not waking up",
        "behosh", "hosh mein nahi", "बेहोश", "होश में नहीं",
    ]):
        flags.append("loss_of_consciousness")
    if _contains_any(lower, [
        "swollen lips", "swelling of lips", "tongue swelling", "face swelling",
        "anaphylaxis", "allergic reaction", "hives", "jeebh sooj", "honth sooj",
        "जीभ सूज", "होंठ सूज",
    ]):
        flags.append("anaphylaxis")
    if _contains_any(lower, ["poison", "overdose", "ingested chemicals", "toxic substance", "drunk cleaning fluid", "chemical exposure"]):
        flags.append("poisoning")
    if _contains_any(lower, ["head injury", "hit my head", "fall and hit head", "concussion", "severe head trauma"]):
        flags.append("head_injury")
    if _contains_any(lower, ["pregnant", "pregnancy"]) and _contains_any(lower, ["severe bleeding", "bleeding", "abdominal pain", "pain in stomach", "heavy bleeding"]):
        flags.append("pregnancy_emergency")
    if _contains_any(lower, ["baby", "infant", "newborn", "child"]) and _contains_any(lower, ["fever", "lethargic", "not waking", "difficult to wake", "blue lips"]):
        flags.append("infant_critical")
    if _contains_any(lower, _self_harm_patterns()):
        flags.append("self_harm")
    if _contains_any(lower, _prompt_injection_patterns()):
        flags.append("prompt_injection")
    return flags


def evaluate_triage(text: str, *, age_band: str | None = None, pregnancy: bool = False, chronic_condition: bool = False) -> TriageResult:
    lower = _normalise_text(text)
    flags = _obvious_red_flags(lower)

    emergency_flags = {
        "chest_pain", "breathing", "stroke", "severe_bleeding", "seizure",
        "loss_of_consciousness", "anaphylaxis", "poisoning", "head_injury",
        "pregnancy_emergency", "infant_critical", "self_harm",
    }
    if "self_harm" in flags:
        return TriageResult(
            urgency="emergency",
            category="mental_health",
            summary="The symptoms suggest immediate risk to the person’s safety or severe mental-health distress.",
            guidance="Call Tele-MANAS 14416 immediately and contact 112 or a trusted emergency contact. Do not leave the person alone if there is immediate danger.",
            emergency_numbers=["Tele-MANAS 14416", "112", "108"],
            flags=flags,
        )

    if any(flag in flags for flag in emergency_flags):
        return TriageResult(
            urgency="emergency",
            category="emergency",
            summary="The reported symptoms meet emergency red-flag criteria and require immediate medical attention.",
            guidance="Call 112 for emergency assistance and 108 for ambulance support. Go to the nearest emergency-capable hospital or urgent care center without delay.",
            emergency_numbers=["112", "108"],
            flags=flags,
        )

    if "prompt_injection" in flags:
        return TriageResult(
            urgency="urgent",
            category="safety",
            summary="The message appears to try to override the safety instructions for this assistant.",
            guidance="Share only symptoms and relevant context. I can help with general, non-diagnostic guidance and safe next steps.",
            emergency_numbers=["112"],
            safety_block=True,
            flags=flags,
        )

    if age_band in {"infant", "child"} or pregnancy or chronic_condition:
        if _contains_any(lower, ["fever", "vomiting", "dizziness", "severe pain", "shortness of breath", "confusion"]):
            return TriageResult(
                urgency="urgent",
                category="special_population",
                summary="The symptoms may need clinician review soon because this person is in a higher-risk group.",
                guidance="Please contact a doctor or nearest urgent care center promptly, and use an emergency service if symptoms worsen.",
                emergency_numbers=["112", "108"],
                flags=flags,
            )

    if _contains_any(lower, ["severe pain", "uncontrolled fever", "vomiting blood", "difficulty walking", "severe dehydration", "dizziness"]) or _contains_any(lower, ["bad pain", "really painful", "cannot walk", "very weak"]):
        return TriageResult(
            urgency="urgent",
            category="urgent",
            summary="The reported symptoms may need same-day clinical review but are not yet showing the strongest emergency signs.",
            guidance="Arrange a same-day assessment with a clinician or urgent care center. If symptoms worsen or new red flags appear, go to emergency care immediately.",
            emergency_numbers=["112", "108"],
            flags=flags,
        )

    return TriageResult(
        urgency="routine",
        category="advice",
        summary="The symptoms are not clearly matching emergency red flags.",
        guidance="Use home-care measures, hydration, rest, and monitor symptoms; if they persist or worsen, seek medical attention from a doctor or clinic.",
        emergency_numbers=[],
        flags=flags,
    )
