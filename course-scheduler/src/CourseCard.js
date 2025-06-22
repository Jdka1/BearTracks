import React from "react";
import "./CourseCard.css";

export default function CourseCard({ course }) {
  return (
    <div className="course-card">
      <div className="course-header">
        <strong>{course.courseCode}</strong>
        <span>{course.courseName}</span>
      </div>
      <div className="course-details">
        <div><strong>Department:</strong> {course.department}</div>
        <div><strong>Units:</strong> {course.units}</div>
        <div><strong>Time:</strong> {course.days} {course.startTime}-{course.endTime}</div>
        <div><strong>Location:</strong> {course.location}</div>
        <div><strong>Instructor:</strong> {course.instructor}</div>
      </div>
      <div className="course-description">
        {course.description}
      </div>
    </div>
  );
}
