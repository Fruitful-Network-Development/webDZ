(() => {
  let currentlyPlaying = null;

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
    const total = Math.floor(seconds);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    return `${pad2(mins)}:${pad2(secs)}`;
  }

  function updatePillUI(pill) {
    const audio = pill.querySelector("audio");
    const button = pill.querySelector(".oral-player__button");
    const progress = pill.querySelector(".oral-player__progress");
    const time = pill.querySelector(".oral-player__time");
    if (!audio || !button || !progress || !time) return;

    const durationText = Number.isFinite(audio.duration) ? formatTime(audio.duration) : "--:--";
    time.textContent = `${formatTime(audio.currentTime)} / ${durationText}`;

    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      const pct = Math.max(0, Math.min(1, audio.currentTime / audio.duration)) * 100;
      progress.style.width = `${pct}%`;
    } else {
      progress.style.width = "0%";
    }

    const isPlaying = !audio.paused && !audio.ended;
    button.textContent = isPlaying ? "Pause" : "Play";
    button.setAttribute("aria-pressed", isPlaying ? "true" : "false");
  }

  function wireAudioPills(root = document) {
    const scope = root && typeof root.querySelectorAll === "function" ? root : document;
    const pills = Array.from(scope.querySelectorAll(".oral-player")).filter(
      (pill) => pill.dataset.audioBound !== "true"
    );
    if (!pills.length) return;

    pills.forEach((pill) => {
      const audio = pill.querySelector("audio");
      const button = pill.querySelector(".oral-player__button");
      const bar = pill.querySelector(".oral-player__bar");
      if (!audio || !button || !bar) return;

      pill.dataset.audioBound = "true";
      button.setAttribute("aria-pressed", "false");
      updatePillUI(pill);

      button.addEventListener("click", async () => {
        if (audio.readyState === 0 && !audio.src) return;

        try {
          if (!audio.paused && !audio.ended) {
            audio.pause();
            return;
          }

          if (currentlyPlaying && currentlyPlaying !== audio) {
            currentlyPlaying.pause();
          }
          currentlyPlaying = audio;
          await audio.play();
        } catch (err) {
          button.disabled = true;
          button.textContent = "Unavailable";
        } finally {
          updatePillUI(pill);
        }
      });

      bar.addEventListener("click", (e) => {
        if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
        const rect = bar.getBoundingClientRect();
        const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
        const pct = rect.width > 0 ? x / rect.width : 0;
        audio.currentTime = pct * audio.duration;
        updatePillUI(pill);
      });

      audio.addEventListener("loadedmetadata", () => updatePillUI(pill));
      audio.addEventListener("durationchange", () => updatePillUI(pill));
      audio.addEventListener("timeupdate", () => updatePillUI(pill));
      audio.addEventListener("play", () => updatePillUI(pill));
      audio.addEventListener("pause", () => updatePillUI(pill));
      audio.addEventListener("ended", () => updatePillUI(pill));
      audio.addEventListener("error", () => {
        button.disabled = true;
        button.textContent = "Unavailable";
      });
    });
  }

  window.initOralPlayers = wireAudioPills;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireAudioPills);
  } else {
    wireAudioPills();
  }
})();
