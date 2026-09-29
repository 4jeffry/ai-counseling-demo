let currentMode = "efficient";
let currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);
let isCalling = false;
let recognition = null;

// Element DOM
const startScreen = document.getElementById("start-screen");
const sessionScreen = document.getElementById("session-screen");
const avatarDisplay = document.getElementById("avatar-display");
const avatarStateText = document.getElementById("avatar-state-text");
const modeButtons = document.querySelectorAll(".mode-btn");
const chatHistory = document.getElementById("chat-history");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const holdSpeakBtn = document.getElementById("hold-speak-btn");
const toggleCallBtn = document.getElementById("toggle-call-btn");

// Pilih Mode (Efficient / Premium)
modeButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        modeButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;
    });
});

// Step 6: State Machine Avatar (IDLE, LISTENING, THINKING, SPEAKING)
function setAvatarState(state) {
    avatarDisplay.className = `avatar ${state.toLowerCase()}`;
    avatarStateText.innerText = `State: ${state.toUpperCase()}`;
}

// Tambah Pesan ke Chat History
function appendMessage(role, text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `msg ${role}`;
    msgDiv.innerText = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Inisialisasi Speech Recognition (Step 5 - STT)
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'id-ID';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        setAvatarState("LISTENING");
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
            sendMessage(transcript);
        } else {
            setAvatarState("IDLE");
        }
    };

    recognition.onerror = () => {
        setAvatarState("IDLE");
        if (isCalling) {
            setTimeout(() => { if (isCalling) recognition.start(); }, 1000);
        }
    };

    recognition.onend = () => {
        if (!isCalling && avatarDisplay.classList.contains("listening")) {
            setAvatarState("IDLE");
        }
    };
}

// Fitur Push-to-Talk (Efficient Mode)
if (holdSpeakBtn) {
    holdSpeakBtn.addEventListener("click", () => {
        if (recognition) {
            recognition.start();
        } else {
            alert("Fitur perekaman suara tidak didukung di browser ini. Silakan gunakan input teks.");
        }
    });
}

// Fitur Continuous Voice Call (Premium Mode)
if (toggleCallBtn) {
    toggleCallBtn.addEventListener("click", () => {
        if (!recognition) {
            alert("Fitur suara tidak didukung di browser ini.");
            return;
        }

        isCalling = !isCalling;
        if (isCalling) {
            toggleCallBtn.innerText = "🛑 End Voice Call";
            toggleCallBtn.classList.add("active");
            recognition.start();
        } else {
            toggleCallBtn.innerText = "📞 Start Voice Call";
            toggleCallBtn.classList.remove("active");
            recognition.stop();
            setAvatarState("IDLE");
        }
    });
}

// Kirim Pesan ke Backend API
async function sendMessage(text) {
    if (!text.trim()) return;

    appendMessage("user", text);
    messageInput.value = "";
    setAvatarState("THINKING");

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: text,
                mode: currentMode
            })
        });

        const data = await response.json();
        if (response.ok) {
            appendMessage("ai", data.reply);
            handleSpeechOutput(data.reply, data.audio_base64);
        } else {
            appendMessage("ai", "Maaf, terjadi kesalahan pada sistem.");
            setAvatarState("IDLE");
        }
    } catch (err) {
        appendMessage("ai", "Gagal terhubung ke server.");
        setAvatarState("IDLE");
    }
}

// Step 4: Handle Output Suara (TTS Browser / ElevenLabs)
function handleSpeechOutput(text, audioBase64) {
    setAvatarState("SPEAKING");

    // Jika Mode Premium & menerima Audio Base64 dari ElevenLabs
    if (currentMode === "premium" && audioBase64) {
        const audio = new Audio("data:audio/mp3;base64," + audioBase64);
        audio.play();
        audio.onended = () => {
            setAvatarState("IDLE");
            if (isCalling && recognition) recognition.start(); // Loop voice call
        };
        audio.onerror = () => {
            // Fallback ke browser TTS jika audio ElevenLabs gagal diputar
            fallbackBrowserTTS(text);
        };
    } else {
        // Mode Efficient menggunakan Browser Native TTS
        fallbackBrowserTTS(text);
    }
}

function fallbackBrowserTTS(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "id-ID";
        utterance.onend = () => {
            setAvatarState("IDLE");
            if (isCalling && recognition) recognition.start();
        };
        utterance.onerror = () => {
            setAvatarState("IDLE");
        };
        window.speechSynthesis.speak(utterance);
    } else {
        setAvatarState("IDLE");
    }
}

// Tombol Kirim Teks
sendBtn.addEventListener("click", () => sendMessage(messageInput.value));
messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage(messageInput.value);
});

// Memulai Sesi
document.getElementById("start-btn").addEventListener("click", () => {
    startScreen.classList.add("hidden");
    sessionScreen.classList.remove("hidden");
    document.getElementById("mode-tag").innerText = `Mode: ${currentMode.toUpperCase()}`;

    if (currentMode === "premium") {
        document.getElementById("efficient-controls").classList.add("hidden");
        document.getElementById("premium-controls").classList.remove("hidden");
    } else {
        document.getElementById("efficient-controls").classList.remove("hidden");
        document.getElementById("premium-controls").classList.add("hidden");
    }

    setAvatarState("IDLE");
    appendMessage("ai", "Halo! Saya di sini siap mendengarkan. Ada yang ingin Anda ceritakan hari ini?");
});

// Mengakhiri Sesi
document.getElementById("end-session-btn").addEventListener("click", () => {
    isCalling = false;
    if (recognition) recognition.stop();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    sessionScreen.classList.add("hidden");
    startScreen.classList.remove("hidden");
    chatHistory.innerHTML = "";
    setAvatarState("IDLE");
});
// Langkah 8: Inisialisasi Discord Embedded App SDK
async function initDiscordSdk() {
    if (window.DiscordSDK) {
        try {
            const discordSdk = new window.DiscordSDK.DiscordSDK(
                // Client ID akan dibaca jika dijalankan sebagai Discord Activity
                window.location.search.get("client_id") || ""
            );
            await discordSdk.ready();
            console.log("Discord Activity SDK Ready!");
        } catch (e) {
            console.log("Dijalankan di luar Discord (Standalone Browser Mode)");
        }
    }
}

initDiscordSdk();
