import React, { useMemo, useState, useEffect } from "react";
import CalendarDayCell from "./CalendarDayCell";
import { getWeekendDaysForRotation } from "../../utils/constants";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getLocalDateString(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function CalendarGrid({
  selectedEmployee,
  year,
  month,
  attendanceHistory = [],
  selectedHistoryDay,
  onSelectDay,
}) {
  // Dynamically compute today's local date string and keep it synced
  const [todayStr, setTodayStr] = useState(() => getLocalDateString());

  useEffect(() => {
    const updateToday = () => {
      const current = getLocalDateString();
      setTodayStr((prev) => (prev !== current ? current : prev));
    };

    // Check periodically so the current date highlight updates dynamically at midnight
    const interval = setInterval(updateToday, 60000);
    window.addEventListener("focus", updateToday);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", updateToday);
    };
  }, []);

  // Build grid cells with Monday-first indexing matching the screenshot
  const cells = useMemo(() => {
    const list = [];
    // In JS: 0=Sun, 1=Mon, ..., 6=Sat.
    // Convert to Monday-first: 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
    const firstDayWeekday = (new Date(year, month - 1, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month, 0).getDate();
    const daysInPrevMonth = new Date(year, month - 1, 0).getDate();

    // 1. Trailing days from previous month
    for (let i = firstDayWeekday - 1; i >= 0; i--) {
      const dayNum = daysInPrevMonth - i;
      list.push({
        key: `prev-${dayNum}`,
        dayNumber: dayNum,
        isCurrentMonth: false,
        isToday: false,
        isSelected: false,
        attendanceData: null,
        statusType: "inactive",
        statusLabel: "",
      });
    }

    const weekendDays = getWeekendDaysForRotation(selectedEmployee?.rotational_weekend);

    // 2. Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      const weekdayIndex = (firstDayWeekday + day - 1) % 7;
      const mm = String(month).padStart(2, "0");
      const dd = String(day).padStart(2, "0");
      const dateStr = `${year}-${mm}-${dd}`;
      const isConfiguredWeekend = weekendDays.includes(weekdayIndex);

      const attendanceData =
        attendanceHistory.find(
          (d) => d.date === dateStr || Number(d.day) === day
        ) || {
          day,
          date: dateStr,
          status:
            isConfiguredWeekend
              ? "WEEKEND"
              : dateStr > todayStr
              ? "UPCOMING"
              : "ABSENT",
          worked_hours: null,
          worked_minutes: 0,
          events: [],
          sessions: [],
        };

      // Determine statusType & statusLabel matching the design
      let statusType = "absent";
      let statusLabel = "Absent";

      const isLeave =
        attendanceData.status === "LEAVE" ||
        Boolean(attendanceData.leave_type);
      const isHalfDay =
        attendanceData.status === "HALF_DAY" ||
        attendanceData.status === "HALF DAY" ||
        attendanceData.status === "HD" ||
        (!attendanceData.status &&
          attendanceData.worked_minutes >= 240 &&
          attendanceData.worked_minutes < 360);
      const isPresent =
        attendanceData.status === "FULL_DAY" ||
        attendanceData.status === "PRESENT" ||
        (!isHalfDay &&
          ((attendanceData.worked_minutes && attendanceData.worked_minutes >= 360) ||
            (!attendanceData.status && Boolean(attendanceData.first_in))));

      const isWeekend = isConfiguredWeekend || attendanceData.status === "WEEKEND";
      const hasCheckIn = Boolean(attendanceData.first_in) || (Number(attendanceData.worked_minutes || 0) > 0);

      // Precedence: Leave -> Actual Check-in (Present/Half Day) -> Weekend (Weekly Off) -> Upcoming -> Absent
      if (isLeave) {
        statusType = "leave";
        statusLabel = "Leave";
      } else if (hasCheckIn && (isPresent || isHalfDay)) {
        if (isHalfDay) {
          statusType = "half-day";
          statusLabel = "Half Day";
        } else {
          statusType = "present";
          statusLabel = "Present";
        }
      } else if (isWeekend) {
        statusType = "weekend";
        statusLabel = "";
      } else if (dateStr > todayStr) {
        statusType = "upcoming";
        statusLabel = "Upcoming";
      } else {
        statusType = "absent";
        statusLabel = "Absent";
      }

      list.push({
        key: `current-${day}`,
        dayNumber: day,
        date: dateStr,
        isCurrentMonth: true,
        isToday: dateStr === todayStr,
        isSelected: selectedHistoryDay?.date === dateStr,
        attendanceData,
        statusType,
        statusLabel,
      });
    }

    // 3. Leading days of next month (completing full 35 or 42 grid rows)
    const totalRequired = Math.ceil((firstDayWeekday + daysInMonth) / 7) * 7;
    const nextDaysCount = totalRequired - (firstDayWeekday + daysInMonth);
    for (let n = 1; n <= nextDaysCount; n++) {
      list.push({
        key: `next-${n}`,
        dayNumber: n,
        isCurrentMonth: false,
        isToday: false,
        isSelected: false,
        attendanceData: null,
        statusType: "inactive",
        statusLabel: "",
      });
    }

    return list;
  }, [year, month, attendanceHistory, selectedHistoryDay, todayStr, selectedEmployee?.rotational_weekend]);

  return (
    <div className="miracle-cal-grid-column-v2">
      {/* Weekday headers row (Mon ... Sun) */}
      <div className="miracle-cal-weekdays-row-v2">
        {WEEKDAYS.map((weekday) => (
          <div key={weekday} className="miracle-cal-weekday-header-v2">
            {weekday}
          </div>
        ))}
      </div>

      {/* 7-column day card grid */}
      <div className="miracle-cal-days-grid-v2">
        {cells.map((cell) => (
          <CalendarDayCell
            key={cell.key}
            cell={cell}
            onSelectDay={onSelectDay}
          />
        ))}
      </div>
    </div>
  );
}
