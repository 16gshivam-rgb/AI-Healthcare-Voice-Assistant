import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "../services/api";
import NotificationContactForm from "./NotificationContactForm";

function countLabel(metric) {
  if (!metric) return "0";
  return metric.suppressed ? "<5 (suppressed)" : String(metric.count);
}

function AdminSection({ title, children }) {
  return <section className="cv-card cv-admin-section"><h2>{title}</h2>{children}</section>;
}

export default function AdminManagement({ token, user, onUserUpdated, language = "en" }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [draftRoles, setDraftRoles] = useState({});
  const [accountForm, setAccountForm] = useState({
    full_name: "",
    email: "",
    role: user?.role === "platform_admin" ? "hospital_admin" : "doctor",
    hospital_id: "",
    doctor_id: "",
    password: "",
    password_confirmation: "",
  });
  const hi = language === "hi";
  const platformAdmin = user?.role === "platform_admin";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [overview, users, appointments, payments, audit, notifications, hospitals, doctors] = await Promise.all([
        apiRequest("/admin/overview", token),
        apiRequest("/admin/users?limit=50", token),
        apiRequest("/admin/appointments?limit=50", token),
        apiRequest("/admin/payments?limit=50", token),
        apiRequest("/admin/audit-logs?limit=50", token),
        apiRequest("/admin/notifications?limit=50", token),
        apiRequest("/admin/hospitals", token),
        apiRequest("/admin/doctors", token),
      ]);
      setData({ overview, users: users.items, appointments: appointments.items, payments: payments.items, audit: audit.items, notifications: notifications.items, hospitals, doctors });
      if (user?.hospital_id) setAccountForm((current) => ({ ...current, hospital_id: String(user.hospital_id) }));
    } catch (reason) {
      setError(reason?.message || (hi ? "प्रशासन की जानकारी लोड नहीं हो सकी।" : "Administration data could not be loaded."));
    } finally {
      setLoading(false);
    }
  }, [token, hi]);

  useEffect(() => { load(); }, [load]);

  async function updateUser(account) {
    setBusyId(`user-${account.id}`);
    setError("");
    setNotice("");
    const body = platformAdmin
      ? { role: draftRoles[account.id] || account.role }
      : { is_active: !account.is_active };
    try {
      await apiRequest(`/admin/users/${account.id}`, token, { method: "PATCH", body: JSON.stringify(body) });
      setNotice(hi ? "खाता अपडेट हुआ।" : "Account updated. Existing sessions were revoked where applicable.");
      await load();
    } catch (reason) {
      setError(reason?.message || (hi ? "खाता अपडेट नहीं हो सका।" : "Account could not be updated."));
    } finally {
      setBusyId(null);
    }
  }

  async function updateAppointment(appointment, action) {
    setBusyId(`appointment-${appointment.id}`);
    setError("");
    setNotice("");
    try {
      const path = `/providers/appointments/${appointment.id}/${action}`;
      await apiRequest(path, token, { method: action === "confirm" ? "POST" : "PATCH", ...(action === "cancel" ? { body: JSON.stringify({}) } : {}) });
      setNotice(hi ? "अपॉइंटमेंट अपडेट हुआ।" : "Appointment updated.");
      await load();
    } catch (reason) {
      setError(reason?.message || (hi ? "अपॉइंटमेंट अपडेट नहीं हो सका।" : "Appointment could not be updated."));
    } finally {
      setBusyId(null);
    }
  }

  async function createAccount(event) {
    event.preventDefault();
    setBusyId("create-account");
    setError("");
    setNotice("");
    if (accountForm.password !== accountForm.password_confirmation) {
      setError(hi ? "पासवर्ड मेल नहीं खाते।" : "Passwords do not match.");
      setBusyId(null);
      return;
    }
    try {
      const account = await apiRequest("/admin/accounts", token, {
        method: "POST",
        body: JSON.stringify({
          full_name: accountForm.full_name,
          email: accountForm.email,
          role: accountForm.role,
          hospital_id: Number(accountForm.hospital_id),
          ...(accountForm.role === "doctor" ? { doctor_id: Number(accountForm.doctor_id) } : {}),
          password: accountForm.password,
          password_confirmation: accountForm.password_confirmation,
        }),
      });
      setNotice(hi
        ? `खाता #${account.id} बनाया गया (${account.role.replaceAll("_", " ")}, अस्पताल #${account.hospital_id})।`
        : `Account #${account.id} created: ${account.role.replaceAll("_", " ")} for hospital #${account.hospital_id}.`);
      setAccountForm((current) => ({
        ...current,
        full_name: "",
        email: "",
        role: platformAdmin ? "hospital_admin" : "doctor",
        doctor_id: "",
        password: "",
        password_confirmation: "",
      }));
      await load();
    } catch (reason) {
      setError(reason?.message || (hi ? "खाता नहीं बनाया जा सका।" : "Account could not be created."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="cv-admin-management">
      <div className="cv-admin-heading">
        <div><span className="eyebrow">{hi ? "प्रशासन" : "ADMINISTRATION"}</span><h2>{hi ? "प्रशासन कार्यक्षेत्र" : "Administration workspace"}</h2>
          <p>{hi ? "डेटा सीधे डेटाबेस से है। कोई डेमो रिकॉर्ड शामिल नहीं है।" : "Live database data only. Demo records are not included."}</p>
        </div>
        <button className="cv-button cv-button-quiet" onClick={load} disabled={loading}>{hi ? "रीफ़्रेश" : "Refresh"}</button>
      </div>
      {error && <div className="cv-error" role="alert">{error}</div>}
      {notice && <div className="cv-success" role="status">{notice}</div>}
      {loading && <div className="cv-loading" role="status">{hi ? "प्रशासन डेटा लोड हो रहा है…" : "Loading administration data…"}</div>}
      {data && (
        <>
          <NotificationContactForm token={token} user={user} onUpdated={onUserUpdated} language={language} />
          <div className="cv-metrics">
            {Object.entries(data.overview.users_by_role).map(([role, metric]) => <article className="cv-metric" key={role}><span className="cv-metric-label">{role.replaceAll("_", " ")}</span><strong>{countLabel(metric)}</strong><small>{hi ? "सक्रिय खाते; छोटे समूह छिपाए गए" : "Active accounts; small counts suppressed"}</small></article>)}
            {Object.entries(data.overview.appointments_by_status).map(([state, metric]) => <article className="cv-metric" key={`appointment-${state}`}><span className="cv-metric-label">{hi ? "अपॉइंटमेंट" : "Appointments"} · {state}</span><strong>{countLabel(metric)}</strong><small>{hi ? "एकत्रित स्थिति" : "Aggregated status"}</small></article>)}
          </div>
          <p className="cv-subtle">{hi ? "स्रोत: डेटाबेस · डेमो रिकॉर्ड: नहीं · 5 से कम समूह गणनाएँ गोपनीयता के लिए छिपाई गई हैं।" : "Source: database · Demo records: none · Counts below five are suppressed for privacy."}</p>

          <AdminSection title={hi ? "खाता और भूमिका प्रबंधन" : "User roles and account access"}>
            {data.users.length ? <div className="cv-admin-table-wrap"><table className="cv-admin-table"><thead><tr><th>Account</th><th>Role</th><th>Hospital</th><th>Status</th><th>Action</th></tr></thead><tbody>
              {data.users.map((account) => <tr key={account.id}>
                <td>{account.full_name}<small>{account.email}</small></td>
                <td>{platformAdmin ? <select aria-label={`Role for ${account.full_name}`} value={draftRoles[account.id] || account.role} onChange={(event) => setDraftRoles({ ...draftRoles, [account.id]: event.target.value })}>{[...(account.doctor_id ? ["doctor"] : []), "hospital_staff", "hospital_admin"].map((role) => <option key={role}>{role}</option>)}</select> : account.role}</td>
                <td>{account.hospital_id ?? "—"}</td><td>{account.is_active ? "Active" : "Inactive"}</td>
                <td><button className="cv-button cv-button-quiet" disabled={busyId === `user-${account.id}`} onClick={() => updateUser(account)}>{platformAdmin ? "Save role" : account.is_active ? "Deactivate" : "Reactivate"}</button></td>
              </tr>)}
            </tbody></table></div> : <p className="cv-subtle">No managed staff accounts.</p>}
          </AdminSection>

          <AdminSection title={hi ? "स्टाफ खाता बनाएँ" : "Create a staff account"}>
            <form className="cv-form" onSubmit={createAccount}>
              <div className="cv-form-row">
                <label>{hi ? "पूरा नाम" : "Full name"}<input required minLength={2} maxLength={120} autoComplete="name" value={accountForm.full_name} onChange={(event) => setAccountForm({ ...accountForm, full_name: event.target.value })} /></label>
                <label>{hi ? "ईमेल" : "Email"}<input required type="email" maxLength={254} autoComplete="email" value={accountForm.email} onChange={(event) => setAccountForm({ ...accountForm, email: event.target.value })} /></label>
              </div>
              {platformAdmin && <label>{hi ? "भूमिका" : "Role"}<select value={accountForm.role} onChange={(event) => setAccountForm({ ...accountForm, role: event.target.value, doctor_id: "" })}><option value="hospital_admin">Hospital administrator</option><option value="doctor">Doctor login</option></select></label>}
              {platformAdmin && <label>{hi ? "अस्पताल" : "Hospital"}<select required value={accountForm.hospital_id} onChange={(event) => setAccountForm({ ...accountForm, hospital_id: event.target.value, doctor_id: "" })}><option value="">Select hospital</option>{data.hospitals.map((hospital) => <option key={hospital.id} value={hospital.id}>#{hospital.id} · {hospital.name} ({hospital.verification_status})</option>)}</select></label>}
              {!platformAdmin && <p className="cv-subtle">{hi ? `अस्पताल #${user.hospital_id} के लिए डॉक्टर लॉगिन बनाया जाएगा।` : `This doctor account will be assigned to your hospital (#${user.hospital_id}).`}</p>}
              {accountForm.role === "doctor" && <label>{hi ? "चिकित्सक प्रोफ़ाइल" : "Clinician profile"}<select required value={accountForm.doctor_id} onChange={(event) => setAccountForm({ ...accountForm, doctor_id: event.target.value })}><option value="">Select clinician</option>{data.doctors.filter((doctor) => Number(doctor.hospital_id) === Number(accountForm.hospital_id) && doctor.is_active).map((doctor) => <option key={doctor.id} value={doctor.id}>#{doctor.id} · {doctor.full_name} — {doctor.specialty}</option>)}</select></label>}
              <div className="cv-form-row">
                <label>{hi ? "पासवर्ड (12+ अक्षर)" : "Password (12+ characters)"}<input required type="password" minLength={12} maxLength={128} autoComplete="new-password" value={accountForm.password} onChange={(event) => setAccountForm({ ...accountForm, password: event.target.value })} /></label>
                <label>{hi ? "पासवर्ड की पुष्टि" : "Confirm password"}<input required type="password" minLength={12} maxLength={128} autoComplete="new-password" value={accountForm.password_confirmation} onChange={(event) => setAccountForm({ ...accountForm, password_confirmation: event.target.value })} /></label>
              </div>
              <p className="cv-subtle">{hi ? "पासवर्ड में बड़े/छोटे अक्षर, अंक और विशेष चिह्न शामिल हों।" : "Use uppercase and lowercase letters, a number, and a special character. Share the temporary password securely."}</p>
              <button className="cv-button cv-button-primary" type="submit" disabled={busyId === "create-account" || !data.hospitals.length}>{busyId === "create-account" ? (hi ? "खाता बनाया जा रहा है…" : "Creating account…") : (hi ? "खाता बनाएँ" : "Create account")}</button>
            </form>
          </AdminSection>

          <AdminSection title={hi ? "अपॉइंटमेंट" : "Appointment operations"}>
            {data.appointments.length ? <div className="cv-admin-table-wrap"><table className="cv-admin-table"><thead><tr><th>Appointment</th><th>Clinician</th><th>Time</th><th>Status</th><th>Action</th></tr></thead><tbody>
              {data.appointments.map((appointment) => <tr key={appointment.id}>
                <td>#{appointment.id}</td><td>{appointment.doctor_name}</td><td>{new Intl.DateTimeFormat(hi ? "hi-IN" : "en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" }).format(new Date(appointment.scheduled_for))} IST</td><td>{appointment.status}</td>
                <td>{appointment.status === "scheduled" && <button className="cv-button cv-button-quiet" disabled={busyId === `appointment-${appointment.id}`} onClick={() => updateAppointment(appointment, "confirm")}>Confirm</button>}
                  {["scheduled", "confirmed"].includes(appointment.status) && <button className="cv-button cv-button-quiet" disabled={busyId === `appointment-${appointment.id}`} onClick={() => updateAppointment(appointment, "cancel")}>Cancel</button>}</td>
              </tr>)}
            </tbody></table></div> : <p className="cv-subtle">No appointments in this scope.</p>}
          </AdminSection>

          <AdminSection title={hi ? "भुगतान स्थिति" : "Payment status (read-only)"}>
            {data.payments.length ? <div className="cv-admin-table-wrap"><table className="cv-admin-table"><thead><tr><th>Invoice</th><th>Amount</th><th>Invoice status</th><th>Payment status</th><th>Issue</th></tr></thead><tbody>
              {data.payments.map((payment) => <tr key={payment.id}><td>{payment.invoice_number}</td><td>{new Intl.NumberFormat("en-IN", { style: "currency", currency: payment.currency }).format(payment.amount_minor / 100)}</td><td>{payment.invoice_status}</td><td>{payment.payment_status}</td><td>{payment.failure_code || "—"}</td></tr>)}
            </tbody></table></div> : <p className="cv-subtle">No payment records in this scope.</p>}
          </AdminSection>

          <AdminSection title={hi ? "ऑडिट लॉग" : "Audit log (privacy-limited)"}>
            {data.audit.length ? <div className="cv-admin-table-wrap"><table className="cv-admin-table"><thead><tr><th>Time</th><th>Action</th><th>Actor ID</th><th>Resource</th></tr></thead><tbody>
              {data.audit.map((entry) => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.action}</td><td>{entry.actor_user_id ?? "—"}</td><td>{entry.resource_type || "—"} {entry.resource_id || ""}</td></tr>)}
            </tbody></table></div> : <p className="cv-subtle">No audit records in this scope.</p>}
          </AdminSection>

          <AdminSection title={hi ? "सूचना वितरण" : "Notification delivery outcomes"}>
            {data.notifications.length ? <div className="cv-admin-table-wrap"><table className="cv-admin-table"><thead><tr><th>Time</th><th>Event</th><th>Channel</th><th>Outcome</th></tr></thead><tbody>
              {data.notifications.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.event_type}</td><td>{item.channel}</td><td>{item.status}{item.failure_code ? ` · ${item.failure_code}` : ""}</td></tr>)}
            </tbody></table></div> : <p className="cv-subtle">No notification delivery attempts have been recorded.</p>}
          </AdminSection>
        </>
      )}
    </div>
  );
}
