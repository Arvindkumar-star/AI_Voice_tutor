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

  try {
    const response = await fetch("/api/practice", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      statusEl.textContent = "Error: " + (payload.detail || `Server error (${response.status})`);
      return;
    }

    console.log("RESPONSE DATA:", payload);
    showResult(payload);
    statusEl.textContent = "Done.";
  } catch (error) {
    console.error("Practice request failed:", error);
    statusEl.textContent = "Error: Could not reach the tutor service.";
  }
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