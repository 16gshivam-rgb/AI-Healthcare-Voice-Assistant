import { useState } from "react";
import { apiRequest } from "../services/api";

export default function PublicTriage({ language = "en" }) {
  const [symptoms, setSymptoms] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const hi = language === "hi";

  async function checkSymptoms(event) {
    event.preventDefault();
    if (busy || symptoms.trim().length < 2) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const triage = await apiRequest("/assistant/triage", "", {
        method: "POST",
        body: JSON.stringify({ text: symptoms.trim() }),
      });
      setResult(triage);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="public-triage" aria-labelledby="public-triage-title">
      <span className="eyebrow">{hi ? "खाते की आवश्यकता नहीं" : "NO ACCOUNT REQUIRED"}</span>
      <h2 id="public-triage-title">{hi ? "तत्काल लक्षण जाँचें" : "Check urgent symptoms"}</h2>
      <p>{hi ? "तत्काल, नियम-आधारित सुरक्षा मार्गदर्शन के लिए लक्षण हिंदी या अंग्रेज़ी में बताएँ।" : "Describe symptoms in English, Hindi, or Hinglish for immediate, rule-based safety guidance."}</p>
      <form onSubmit={checkSymptoms}>
        <label htmlFor="public-triage-symptoms">{hi ? "क्या हो रहा है?" : "What is happening?"}</label>
        <textarea
          id="public-triage-symptoms"
          value={symptoms}
          onChange={(event) => setSymptoms(event.target.value)}
          placeholder={hi ? "उदाहरण: सीने में दर्द और साँस लेने में दिक्कत" : "For example: seene mein dard aur saans lene mein dikkat"}
          minLength={2}
          maxLength={4000}
          rows={3}
          required
        />
        <button className="secondary wide" type="submit" disabled={busy || symptoms.trim().length < 2}>
          {busy ? (hi ? "जाँच हो रही है…" : "Checking…") : (hi ? "सुरक्षा मार्गदर्शन पाएँ" : "Get safety guidance")}
        </button>
      </form>
      {error && <div className="notice error" role="alert">{error}</div>}
      {result && (
        <div className={`triage-result ${result.urgency === "emergency" ? "emergency" : ""}`} role={result.urgency === "emergency" ? "alert" : "status"}>
          <b>{result.urgency === "emergency" ? (hi ? "अभी आपातकालीन सहायता लें" : "Seek emergency help now") : `${result.urgency} guidance`}</b>
          <p>{result.summary}</p>
          <p>{result.guidance}</p>
          {result.emergency_numbers.length > 0 && (
            <p><b>{hi ? "आपातकालीन नंबर:" : "Emergency contacts:"}</b> {result.emergency_numbers.map((number, index) => (
              <span key={`${number}-${index}`}>{index > 0 && " · "}<a href={`tel:${String(number).replace(/\D/g, "")}`}>{number}</a></span>
            ))}</p>
          )}
        </div>
      )}
      <p className="triage-disclaimer">
        {hi ? "यह सीमित जाँच आपातकाल को खारिज नहीं कर सकती और निदान नहीं है। खतरा हो तो अभी 112 या 108 पर कॉल करें।" : "This limited check cannot rule out an emergency and is not a diagnosis. If you may be in danger, call 112 or 108 now."}
      </p>
    </section>
  );
}
