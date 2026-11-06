import React from "react";

export default function CalendarDayCell({
  cell,
  onSelectDay,
}) {
  const {
    dayNumber,
    date,
    isCurrentMonth,
    isToday,
    isSelected,
    attendanceData,
    statusType,
    statusLabel,
  } = cell;

  const handleClick = () => {
    if (isCurrentMonth && attendanceData && onSelectDay) {
      onSelectDay(attendanceData);
    }
  };

  const accessibleLabel = isCurrentMonth
    ? `Day ${dayNumber}, ${statusLabel || (statusType === "weekend" ? "Weekend" : "No status")}`
    : `Inactive day ${dayNumber}`;

  return (
    <div
      className={`miracle-cal-day-card-v2 type-${statusType} ${
        isSelected ? "is-selected" : ""
      }`}
      onClick={handleClick}
      role="button"
      tabIndex={isCurrentMonth ? 0 : -1}
      aria-label={accessibleLabel}
      data-date={date}
      title={date ? `${date}` : undefined}
    >
      <span className="miracle-cal-day-num-v2">{dayNumber}</span>
      {statusLabel ? (
        <span className="miracle-cal-day-label-v2">{statusLabel}</span>
      ) : null}
    </div>
  );
}

