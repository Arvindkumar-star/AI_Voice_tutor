let mediaRecorder;
let audioChunks = [];

const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const loadHistoryBtn = document.getElementById("loadHistoryBtn");
const statusEl = document.getElementById("status");

recordBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) {
      audioChunks.push(e.data);
    }
  };
  mediaRecorder.onstop = sendRecording;

  mediaRecorder.start(250);
  statusEl.textContent = "Recording... speak now";
  document.getElementById("recDot").classList.add("active");
  recordBtn.disabled = true;
  stopBtn.disabled = false;
};

stopBtn.onclick = () => {
  mediaRecorder.stop();
  statusEl.textContent = "Processing...";
  document.getElementById("recDot").classList.remove("active");
  recordBtn.disabled = false;
  stopBtn.disabled = true;
};

async function sendRecording() {
  const username = document.getElementById("username").value.trim();
  const language = document.getElementById("language").value.trim();

  if (!username || !language) {
    statusEl.textContent = "Please enter a username and language before recording.";
    return;
  }

  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });

  const formData = new FormData();
  formData.append("username", username);
  formData.append("language", language);
  formData.append("audio", audioBlob, "recording.webm");

  const response = await fetch("/api/practice", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    statusEl.textContent = "Error: " + err.detail;
    return;
  }

  const data = await response.json();
  console.log("RESPONSE DATA:", data);
  showResult(data);
  statusEl.textContent = "Done.";
}

function showResult(d) {
  const card = document.getElementById("resultCard");
  card.style.display = "block";
  document.getElementById("transcript").textContent = d.transcript;
  document.getElementById("corrected").textContent = d.corrected;
  document.getElementById("feedback").textContent = d.feedback;
  document.getElementById("responseAudio").src = d.audio_url;
}

loadHistoryBtn.onclick = async () => {
  const username = document.getElementById("username").value.trim();
  const language = document.getElementById("language").value.trim();

  if (!username || !language) {
    statusEl.textContent = "Please enter a username and language first.";
    return;
  }

  const response = await fetch(`/api/history/${username}/${language}`);
  const data = await response.json();

  const list = document.getElementById("historyList");
  list.innerHTML = "";

  if (data.history.length === 0) {
    list.innerHTML = "<p class='empty-history'>No attempts yet.</p>";
    return;
  }

  data.history.slice().reverse().forEach((attempt) => {
    const div = document.createElement("div");
    div.className = "history-item";
    const badge = attempt.had_errors
      ? '<span class="badge errors">had errors</span>'
      : '<span class="badge correct">correct</span>';
    div.innerHTML = `
      <div class="history-meta">
        <span class="history-date">${new Date(attempt.timestamp).toLocaleString()}</span>
        ${badge}
      </div>
      <div class="history-original">"${attempt.original_text}"</div>
      <div class="history-arrow">→</div>
      <div class="history-corrected">"${attempt.corrected_text}"</div>
    `;
    list.appendChild(div);
  });
};