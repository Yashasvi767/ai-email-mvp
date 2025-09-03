const listEl = document.getElementById("email-list");
const statTotal = document.getElementById("stat-total");
const statResolved = document.getElementById("stat-resolved");
const statPending = document.getElementById("stat-pending");
const statUrgent = document.getElementById("stat-urgent");
const filterInput = document.getElementById("filter");

let currentEmailId = null;

async function fetchEmails(){
  const res = await fetch("/emails");
  return await res.json();
}
async function fetchStats(){
  const res = await fetch("/stats/24h");
  return await res.json();
}

async function refreshAll(){
  const emails = await fetchEmails();
  renderList(emails);
  const stats = await fetchStats();
  statTotal.innerText = stats.total;
  statResolved.innerText = stats.resolved;
  statPending.innerText = stats.pending;
  statUrgent.innerText = stats.urgent;
  renderChart(stats.by_sentiment);
}

function renderList(items){
  const q = filterInput.value.toLowerCase().trim();
  listEl.innerHTML = "";
  items.forEach(it=>{
    if(q && !(it.subject||"").toLowerCase().includes(q) && !(it.body_text||"").toLowerCase().includes(q)) return;
    const li = document.createElement("li");
    li.innerHTML = `<strong>${it.subject}</strong><div style="font-size:12px;color:#555">${it.sender} • ${new Date(it.received_at).toLocaleString()}</div>`;
    if(it.urgency === "urgent") li.classList.add("urgent");
    li.onclick = ()=> selectEmail(it.id);
    listEl.appendChild(li);
  });
}

async function selectEmail(id){
  currentEmailId = id;
  const res = await fetch(`/emails/${id}`);
  const data = await res.json();
  document.getElementById("detail-subject").innerText = data.subject || "";
  document.getElementById("detail-sender").innerText = data.sender || "";
  document.getElementById("detail-received").innerText = new Date(data.received_at).toLocaleString();
  document.getElementById("detail-sentiment").innerText = data.sentiment || "";
  document.getElementById("detail-urgency").innerText = data.urgency || "";
  document.getElementById("detail-body").innerText = data.body_text || "";
  document.getElementById("detail-phone").innerText = (data.ner_json && data.ner_json.phones && data.ner_json.phones[0]) || "";
  document.getElementById("detail-summary").innerText = data.summary || "";
  document.getElementById("draft").value = data.draft || "";
}

document.getElementById("send-btn").onclick = async ()=>{
  if(!currentEmailId) return alert("Select an email first");
  const final_text = document.getElementById("draft").value;
  const res = await fetch(`/emails/${currentEmailId}/respond`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({final_text})
  });
  if(res.ok){
    alert("Sent (stub). Check data/sent_emails.log in container.");
    await refreshAll();
  } else {
    alert("Failed to send");
  }
};

document.getElementById("refresh-btn").onclick = refreshAll;
filterInput.oninput = refreshAll;

let sentimentChart = null;
function renderChart(data){
  const ctx = document.getElementById("sentimentChart").getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data);
  if(sentimentChart) sentimentChart.destroy();
  sentimentChart = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values }]},
    options: { responsive: true }
  });
}

refreshAll();
