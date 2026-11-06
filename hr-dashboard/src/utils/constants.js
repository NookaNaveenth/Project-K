// Shared constants for company-wide standardized Department, Practice, and Team dropdowns

export const STANDARDIZED_DEPARTMENTS = [
  "Executive Board",
  "Marketing",
  "Operations",
  "Recruitment",
  "Sales",
  "Software Services",
];

export const SOFTWARE_SERVICES_PRACTICES = [
  "App Dev",
  "Miracle Apps",
  "Cloud and DevOps",
  "Data and Analytics",
  "SAP",
  "Integration",
  "Q/A and Testing",
  "Innovation",
  "Process Automation",
];

export const STANDARDIZED_PRACTICES = SOFTWARE_SERVICES_PRACTICES;

export const DEPARTMENT_TEAMS = {
  "Recruitment": [
    "US IT",
    "Domestic IT",
    "Sourcing",
  ],
  "Sales": [
    "Inside Sales",
    "Software Sales",
    "Field Sales",
    "Bench Sales",
    "Deals",
  ],
  "Operations": [
    "IT Team",
    "Human Resources",
    "Immigration",
    "Invoicing",
    "Payroll",
    "MILE",
    "Project Management",
    "Accounts",
    "Legal",
    "Civil",
    "Procurement",
  ],
  "Marketing": [
    "Graphic Designer",
    "Web Experience",
    "Front End Dev",
    "Email Marketing",
    "Demand Generation",
    "Branding & Communication",
    "Content Writer",
    "Social Media Manager / Coordinator",
    "Partnership Executive",
    "UI/UX Designer",
    "Motion Graphic Designer",
    "Director",
  ],
  "Executive Board": [],
  "Software Services": [],
};

export const getPracticesForDepartment = (dept) => {
  if (dept === "Software Services") {
    return SOFTWARE_SERVICES_PRACTICES;
  }
  return [];
};

export const getTeamsForDepartment = (dept) => {
  if (dept && DEPARTMENT_TEAMS[dept]) {
    return DEPARTMENT_TEAMS[dept];
  }
  return [];
};

export const ROTATIONAL_WEEKEND_OPTIONS = [
  "Monday – Tuesday",
  "Tuesday – Wednesday",
  "Wednesday – Thursday",
  "Thursday – Friday",
  "Friday – Saturday",
  "Saturday – Sunday",
  "Sunday – Monday",
];

export const getWeekendDaysForRotation = (rotation) => {
  if (!rotation) return [5, 6];
  const s = String(rotation).replace(/[–—]/g, "-").toLowerCase();
  if (s.includes("monday") && s.includes("tuesday")) return [0, 1];
  if (s.includes("tuesday") && s.includes("wednesday")) return [1, 2];
  if (s.includes("wednesday") && s.includes("thursday")) return [2, 3];
  if (s.includes("thursday") && s.includes("friday")) return [3, 4];
  if (s.includes("friday") && s.includes("saturday")) return [4, 5];
  if (s.includes("saturday") && s.includes("sunday")) return [5, 6];
  if (s.includes("sunday") && s.includes("monday")) return [6, 0];
  return [5, 6];
};

