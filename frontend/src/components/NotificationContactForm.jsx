import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";

export default function NotificationContactForm({ token, user, onUpdated, language = "en" }) {
  const [phone, setPhone] = useState(user?.phone_number || "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const hi = language === "hi";

  useEffect(() => setPhone(user?.phone_number || ""), [user?.phone_number]);

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiRequest("/auth/me", token, {
        method: "PATCH",
        body: JSON.stringify({ phone_number: phone.trim() || null }),
      });
      onUpdated?.(updated);
      setMessage(hi ? "संपर्क नंबर अपडेट हुआ।" : "Contact number updated.");
    } catch (reason) {
      setError(reason?.message || (hi ? "संपर्क नंबर सेव नहीं हुआ।" : "Contact number could not be saved."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="cv-card cv-form cv-contact-settings" onSubmit={save}>
      <h2>{hi ? "सूचना संपर्क" : "Notification contact"}</h2>
      <p className="cv-subtle">{hi ? "SMS वैकल्पिक है। केवल + सहित अंतरराष्ट्रीय प्रारूप में नंबर सेव करें।" : "SMS is optional. Save a number in international format, including the leading +."}</p>
      <label>{hi ? "मोबाइल नंबर" : "Mobile number"}<input type="tel" inputMode="tel" pattern="\\+[1-9][0-9]{7,14}" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+919876543210" /></label>
      {error && <p className="cv-error" role="alert">{error}</p>}
      {message && <p className="cv-success" role="status">{message}</p>}
      <button className="cv-button cv-button-secondary" disabled={busy}>{busy ? (hi ? "सेव हो रहा है…" : "Saving…") : (hi ? "संपर्क सेव करें" : "Save contact")}</button>
    </form>
  );
}
