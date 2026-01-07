TAXONOMY = {
    "VA": {
        "name": "Department of Veterans Affairs",
        "subagencies": {
            "VBA": {
                "name": "Veterans Benefits Administration",
                "programs": {
                    "GI_BILL": {
                        "name": "GI Bill Benefits",
                        "problems": ["Payment Delay", "Eligibility", "Records Request"]
                    },
                    "DISABILITY": {
                        "name": "Disability Compensation",
                        "problems": ["Claims Processing", "Appeal Status", "Payment Delay"]
                    }
                }
            }
        }
    },
    "HHS": {
        "name": "Department of Health and Human Services",
        "subagencies": {
            "CMS": {
                "name": "Centers for Medicare & Medicaid Services",
                "programs": {
                    "MEDICARE_A": {
                        "name": "Medicare Part A",
                        "problems": ["Claims Processing", "Eligibility", "Appeal Status"]
                    },
                    "MEDICARE_B": {
                        "name": "Medicare Part B",
                        "problems": ["Claims Processing", "Coverage Denial", "Eligibility"]
                    }
                }
            }
        }
    },
    "DHS": {
        "name": "Department of Homeland Security",
        "subagencies": {
            "USCIS": {
                "name": "U.S. Citizenship and Immigration Services",
                "programs": {
                    "VISA": {
                        "name": "Visa Processing",
                        "problems": ["Processing Delay", "Documentation Issue", "Status Inquiry"]
                    },
                    "NATURALIZATION": {
                        "name": "Naturalization",
                        "problems": ["Processing Delay", "Interview Scheduling", "Records Request"]
                    }
                }
            }
        }
    },
    "SSA": {
        "name": "Social Security Administration",
        "subagencies": {
            "SSA_MAIN": {
                "name": "SSA Programs",
                "programs": {
                    "SSDI": {
                        "name": "Social Security Disability Insurance",
                        "problems": ["Claims Processing", "Appeal Status", "Payment Delay"]
                    },
                    "RETIREMENT": {
                        "name": "Retirement Benefits",
                        "problems": ["Eligibility", "Payment Delay", "Records Request"]
                    }
                }
            }
        }
    }
}


def get_taxonomy_prompt_list() -> str:
    """Flatten taxonomy into Tier1 → Tier2 → Tier3 → Tier4 paths."""
    paths = []
    for t1_key, t1_data in TAXONOMY.items():
        for t2_key, t2_data in t1_data["subagencies"].items():
            for t3_key, t3_data in t2_data["programs"].items():
                for problem in t3_data["problems"]:
                    paths.append(
                        f"{t1_data['name']} → {t2_data['name']} → {t3_data['name']} → {problem}"
                    )
    return "\n".join(paths)

# Issue Area mapping (Tier 1 agency → Issue Area)
ISSUE_AREAS = {
    "Department of Veterans Affairs": "Veterans",
    "Department of Health and Human Services": "Healthcare",
    "Department of Homeland Security": "Immigration",
    "Social Security Administration": "Benefits",
}


def get_issue_area(tier1: str) -> str:
    """Map Tier 1 agency to Issue Area."""
    return ISSUE_AREAS.get(tier1, "Other")

