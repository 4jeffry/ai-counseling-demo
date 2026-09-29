let currentMode = "efficient";
let currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);
let isCalling = false;
let recognition = null;

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

modeButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        modeButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;
    });
});

function setAvatarState(state) {
    avatarDisplay.className = `avatar ${state.toLowerCase()}`;
    avatarStateText.innerText = `State: ${state.toUpperCase()}`;
}

function appendMessage(role, text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `msg ${role}`;
    msgDiv.innerText = text;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'id-ID';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => { setAvatarState("LISTENING"); };

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

if (holdSpeakBtn) {
    holdSpeakBtn.addEventListener("click", () => {
        if (recognition) recognition.start();
    });
}

if (toggleCallBtn) {
    toggleCallBtn.addEventListener("click", () => {
        if (!recognition) return;
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

// Konversi Base64 ke Blob untuk memotong pembatasan string URL WebView
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteArrays = [];
    for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }
    return new Blob(byteArrays, { type: mimeType });
}

function handleSpeechOutput(text, audioBase64) {
    setAvatarState("SPEAKING");

    if (currentMode === "premium" && audioBase64) {
        try {
            const blob = base64ToBlob(audioBase64, "audio/mpeg");
            const blobUrl = URL.createObjectURL(blob);
            const audio = new Audio(blobUrl);

            // Paksa pemutaran audio
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.then(() => {
                    console.log("Audio ElevenLabs berhasil diputar");
                }).catch(error => {
                    console.log("Autoplay diblokir, fallback ke browser TTS", error);
                    fallbackBrowserTTS(text);
                });
            }

            audio.onended = () => {
                URL.revokeObjectURL(blobUrl);
                setAvatarState("IDLE");
                if (isCalling && recognition) recognition.start();
            };
            audio.onerror = () => {
                URL.revokeObjectURL(blobUrl);
                fallbackBrowserTTS(text);
            };
        } catch (e) {
            fallbackBrowserTTS(text);
        }
    } else {
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
        utterance.onerror = () => { setAvatarState("IDLE"); };
        window.speechSynthesis.speak(utterance);
    } else {
        setAvatarState("IDLE");
    }
}

sendBtn.addEventListener("click", () => sendMessage(messageInput.value));
messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage(messageInput.value);
});

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

document.getElementById("end-session-btn").addEventListener("click", () => {
    isCalling = false;
    if (recognition) recognition.stop();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    sessionScreen.classList.add("hidden");
    startScreen.classList.remove("hidden");
    chatHistory.innerHTML = "";
    setAvatarState("IDLE");
});

async function initDiscordSdk() {
    if (window.DiscordSDK) {
        try {
            const discordSdk = new window.DiscordSDK.DiscordSDK(
                new URLSearchParams(window.location.search).get("client_id") || ""
            );
            await discordSdk.ready();
        } catch (e) {}
    }
}
initDiscordSdk();
