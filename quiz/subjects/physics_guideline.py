"""
Physics Examination Guidelines - Grade 10 & 11 (DBE CAPS)
Used by question generator and grader for keyword accuracy.
"""

# ── Marking rules from DBE guidelines ────────────────────────────
MARKING_RULES = """
PHYSICS MARKING RULES (DBE CAPS):
- Marks awarded for: correct formula + correct substitution + correct answer with unit
- No marks if incorrect formula used, even with correct substitution
- If correct formula but wrong substitution: mark for formula only, no further marks
- If no formula given but all substitutions correct: forfeit ONE mark
- Final answers must be rounded to minimum TWO decimal places
- Units only required in final answer
- Penalised once only for repeated incorrect unit within a question
- Positive marking: if variable incorrectly calculated in subquestion A but correctly
  substituted in subquestion B, full marks awarded for subquestion B
"""

# ── Formula sheets ────────────────────────────────────────────────
FORMULAS_GR10 = {
    "motion": [
        "vf = vi + a·Δt",
        "Δx = vi·Δt + ½·a·Δt²",
        "vf² = vi² + 2·a·Δx",
        "Δx = ((vi + vf)/2)·Δt",
    ],
    "energy": [
        "U = mgh (gravitational potential energy)",
        "Ek = ½mv² (kinetic energy)",
        "EM = Ek + Ep (mechanical energy)",
    ],
    "waves": [
        "v = fλ",
        "T = 1/f",
        "E = hf = hc/λ",
    ],
    "electricity": [
        "Q = I·Δt",
        "V = W/Q",
        "Rs = R1 + R2 + ...",
        "1/Rp = 1/R1 + 1/R2 + ...",
    ],
}

FORMULAS_GR11 = {
    "vectors": [
        "Rx = Rcosθ",
        "Ry = Rsinθ",
        "R = √(Rx² + Ry²)",
        "θ = tan⁻¹(Ry/Rx)",
    ],
    "friction": [
        "fs(max) = μs·N",
        "fk = μk·N",
    ],
    "newton_gravitation": [
        "F = Gm1m2/r²  (G = 6.67 x 10^-11 N·m²·kg⁻²)",
        "g = GM/r²",
        "w = mg",
    ],
    "momentum": [
        "p = mv",
        "Δp = m·Δv = FnetΔt (impulse-momentum theorem)",
        "m1v1i + m2v2i = m1v1f + m2v2f (conservation of momentum)",
    ],
    "work_energy": [
        "W = FΔxcosθ",
        "W = ΔEk = ½mvf² - ½mvi²",
        "P = W/Δt = Fv",
        "Eff = Pout/Pin x 100%",
    ],
    "doppler": [
        "fL = v ± vL / (v ± vs) · fs",
    ],
    "electricity": [
        "R = V/I (Ohm's law)",
        "P = VI = I²R = V²/R",
        "W = VIt = I²Rt",
        "emf = I(R + r)",
        "emf = Vload + Vinternal",
    ],
    "electrostatics": [
        "F = kQ1Q2/r²  (k = 9 x 10^9 N·m²·C⁻²)",
        "E = kQ/r²",
        "E = V/d",
        "V = W/q",
        "C = Q/V",
    ],
}

CONSTANTS = {
    "g": "9.8 m·s⁻²",
    "G": "6.67 x 10^-11 N·m²·kg⁻²",
    "c": "3.0 x 10^8 m·s⁻¹",
    "h": "6.63 x 10^-34 J·s",
    "e": "-1.6 x 10^-19 C",
    "k": "9.0 x 10^9 N·m²·C⁻²",
    "me": "9.11 x 10^-31 kg",
}

# ── Required keywords per topic ───────────────────────────────────
REQUIRED_KEYWORDS = {
    "newton's first law": [
        "remain", "state of rest", "constant velocity",
        "non-zero resultant", "net force"
    ],
    "newton's second law": [
        "resultant", "net force", "directly proportional",
        "inversely proportional", "mass", "acceleration",
        "Fnet = ma"
    ],
    "newton's third law": [
        "simultaneously", "equal magnitude", "opposite direction",
        "action", "reaction", "two bodies"
    ],
    "newton's law of gravitation": [
        "directly proportional", "product of masses",
        "inversely proportional", "square of distance",
        "between their centres", "F = Gm1m2/r²"
    ],
    "momentum": [
        "product of mass and velocity", "vector", "p = mv"
    ],
    "impulse-momentum theorem": [
        "net force", "time", "change in momentum",
        "FnetΔt = Δp"
    ],
    "conservation of momentum": [
        "isolated system", "no external forces",
        "total momentum", "constant", "before", "after"
    ],
    "work": [
        "force", "displacement", "cosθ", "parallel",
        "W = FΔxcosθ"
    ],
    "kinetic energy": [
        "½mv²", "motion", "scalar"
    ],
    "gravitational potential energy": [
        "mgh", "position", "gravitational field", "reference point"
    ],
    "conservation of mechanical energy": [
        "isolated system", "no non-conservative forces",
        "total mechanical energy", "constant",
        "Ek1 + Ep1 = Ek2 + Ep2"
    ],
    "coulomb's law": [
        "directly proportional", "product of charges",
        "inversely proportional", "square of distance",
        "F = kQ1Q2/r²"
    ],
    "electric field": [
        "force per unit positive charge", "E = kQ/r²",
        "direction", "positive test charge"
    ],
    "ohm's law": [
        "potential difference", "directly proportional",
        "current", "constant temperature", "R = V/I"
    ],
    "refraction": [
        "change in direction", "change in speed",
        "different optical density", "medium"
    ],
    "doppler effect": [
        "apparent frequency", "relative motion",
        "source", "observer", "higher", "lower"
    ],
    "photoelectric effect": [
        "threshold frequency", "work function",
        "photon", "electron", "emit", "Ek = hf - W"
    ],
    "weight": [
        "gravitational force", "newton", "w = mg"
    ],
    "normal force": [
        "perpendicular", "surface", "contact"
    ],
    "friction": [
        "opposes motion", "parallel to surface",
        "proportional to normal force"
    ],
    "inertia": [
        "resistance", "change in state of motion", "mass"
    ],
    "weightlessness": [
        "contact forces removed", "free fall",
        "non-contact force", "no sensation"
    ],
}

# ── Topics per grade ──────────────────────────────────────────────
TOPICS_GR10_PHYSICS = [
    "Vectors and scalars",
    "Motion in one dimension",
    "Energy",
    "Transverse pulses",
    "Transverse waves",
    "Longitudinal waves",
    "Sound",
    "Electromagnetic radiation",
    "Magnetism",
    "Electrostatics",
    "Electric circuits",
]

TOPICS_GR10_CHEMISTRY = [
    "Matter and classification",
    "States of matter and kinetic molecular theory",
    "Atomic structure",
    "Periodic table",
    "Chemical bonding",
    "Transverse pulses",
    "Physical and chemical change",
    "Representing chemical change",
    "Reactions in aqueous solutions",
    "Quantitative aspects of chemical change",
    "The hydrosphere",
]

TOPICS_GR11_PHYSICS = [
    "Vectors in two dimensions",
    "Newton's laws of motion",
    "Newton's law of universal gravitation",
    "Momentum and impulse",
    "Work, energy and power",
    "Doppler effect",
    "Refraction and Snell's law",
    "Optical phenomena and properties of matter",
    "Electrostatics",
    "Electric circuits",
    "Electromagnetic induction",
]

TOPICS_GR11_CHEMISTRY = [
    "Intermolecular forces",
    "Atomic combinations and molecular structure",
    "Ideal gases",
    "Quantitative aspects of chemical change",
    "Energy and chemical change",
    "Types of reactions",
    "Electrochemical reactions",
]


def get_keyword_hint(topic):
    """Return required keywords for a given topic for grader use."""
    topic_lower = topic.lower()
    for key, keywords in REQUIRED_KEYWORDS.items():
        if key in topic_lower or topic_lower in key:
            return keywords
    return []


def get_formula_hint(topic):
    """Return relevant formulas for a given topic."""
    topic_lower = topic.lower()
    results = []
    for section, formulas in {**FORMULAS_GR11, **FORMULAS_GR10}.items():
        if section in topic_lower or topic_lower in section:
            results.extend(formulas)
    return results


def get_marking_rules():
    return MARKING_RULES
