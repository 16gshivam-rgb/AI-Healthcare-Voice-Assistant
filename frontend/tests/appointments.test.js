import assert from "node:assert/strict";
import { test } from "node:test";
import {
  createIdempotencyKey,
  formatAppointmentDatePart,
  formatAppointmentDateTime,
  getISTDate,
} from "../src/services/appointments.js";

test("appointment date and time formatting is fixed to IST", () => {
  const instant = "2024-01-01T18:30:00.000Z";
  const formatted = formatAppointmentDateTime(instant, "en-IN");
  assert.match(formatted, /2 Jan, 2024/i);
  assert.match(formatted, /12:00 am/i);
  assert.equal(formatAppointmentDatePart(instant, "day", "en-IN"), "02");
  assert.match(formatAppointmentDatePart(instant, "month", "en-IN"), /Jan/i);
});

test("appointment idempotency keys are non-empty unique command identifiers", () => {
  const first = createIdempotencyKey();
  const second = createIdempotencyKey();
  assert.ok(first.length >= 16);
  assert.notEqual(first, second);
});

test("IST booking date helper returns an ISO calendar date", () => {
  assert.match(getISTDate(2), /^\d{4}-\d{2}-\d{2}$/);
});
