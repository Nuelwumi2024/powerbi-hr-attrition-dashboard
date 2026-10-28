"""Generates the synthetic HR dataset (star schema) used by the Power BI report.

Run from the repo root:  python src/generate_data.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
N = 1500
AS_OF = pd.Timestamp("2025-12-31")

departments = pd.DataFrame({
    "DepartmentID": range(1, 8),
    "Department": ["Engineering", "Sales", "Customer Support", "Marketing", "Finance", "HR", "Operations"],
    "BaseAttrition": [.11, .22, .26, .14, .08, .09, .19],   # drives the synthetic exits
    "BaseSalary": [92000, 68000, 45000, 64000, 78000, 58000, 52000],
})
weights = [.24, .20, .18, .09, .07, .04, .18]
levels = ["Junior", "Mid", "Senior", "Lead", "Manager"]
level_mult = dict(zip(levels, [.75, 1.0, 1.3, 1.6, 1.9]))

dept = rng.choice(departments.DepartmentID, N, p=weights)
level = rng.choice(levels, N, p=[.28, .34, .22, .09, .07])
d = departments.set_index("DepartmentID").loc[dept]
hire = AS_OF - pd.to_timedelta(rng.integers(30, 365 * 9, N), unit="D")
age = np.clip(rng.normal(34, 7, N) + np.array([levels.index(l) for l in level]) * 2, 21, 62).astype(int)
salary = (d.BaseSalary.values * np.array([level_mult[l] for l in level]) * rng.normal(1, .08, N)).round(-2)
overtime = rng.random(N) < .3
satisfaction = np.clip(rng.normal(3.4, 1.0, N).round(), 1, 5).astype(int)
performance = np.clip(rng.normal(3.3, .8, N).round(), 1, 5).astype(int)
remote = rng.choice(["Onsite", "Hybrid", "Remote"], N, p=[.4, .4, .2])

# exit probability: department base rate adjusted by known real-world drivers
p = d.BaseAttrition.values.copy()
p *= np.where(overtime, 1.6, 1.0)
p *= np.where(satisfaction <= 2, 1.8, np.where(satisfaction == 5, .6, 1.0))
p *= np.where(np.array(level) == "Junior", 1.3, 1.0)
p *= np.where(salary < d.BaseSalary.values * .9, 1.4, 1.0)
left = rng.random(N) < np.clip(p, 0, .8)
tenure_days = (AS_OF - hire).days.values
exit_after = (rng.uniform(.2, 1.0, N) * tenure_days).astype(int)
term = pd.Series(pd.NaT, index=range(N), dtype="datetime64[ns]")
term[left] = hire[left] + pd.to_timedelta(exit_after[left], unit="D")
reasons = rng.choice(["Better Compensation", "Career Growth", "Work-Life Balance", "Management",
                      "Relocation", "Retirement", "Performance"], N,
                     p=[.26, .24, .18, .14, .08, .04, .06])

employees = pd.DataFrame({
    "EmployeeID": [f"E{i:04d}" for i in range(1, N + 1)],
    "DepartmentID": dept,
    "JobLevel": level,
    "Gender": rng.choice(["Female", "Male", "Non-binary"], N, p=[.47, .49, .04]),
    "Age": age,
    "HireDate": hire.date if hasattr(hire, "date") else hire,
    "TerminationDate": term.dt.date,
    "ExitReason": np.where(left, reasons, ""),
    "MonthlySalary": (salary / 12).round(0),
    "WorkMode": remote,
    "Overtime": np.where(overtime, "Yes", "No"),
    "SatisfactionScore": satisfaction,
    "PerformanceRating": performance,
})
employees["HireDate"] = pd.to_datetime(employees["HireDate"]).dt.date

departments.drop(columns=["BaseAttrition", "BaseSalary"]).to_csv("data/departments.csv", index=False)
employees.to_csv("data/employees.csv", index=False)
print(f"{N} employees, attrition {left.mean():.1%}, avg monthly salary {employees.MonthlySalary.mean():,.0f}")
