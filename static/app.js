(function () {
  "use strict";

  var urlInput = document.getElementById("url");
  var form = document.getElementById("grab-form");
  var startBtn = document.getElementById("start");
  var destinationInput = document.getElementById("destination");
  var templateInput = document.getElementById("template");
  var audioHelp = document.getElementById("audio-help");
  var audioConsequence = document.getElementById("audio-consequence");
  var destinationChoices = document.getElementById("destination-choices");
  var templatePresets = document.getElementById("template-presets");
  var templateExact = document.getElementById("template-exact");
  var settingsNote = document.getElementById("settings-note");
  var formStatus = document.getElementById("form-status");
  var jobsEl = document.getElementById("jobs");
  var followForm = document.getElementById("follow-form");
  var followInput = document.getElementById("follow-channel");
  var followAdd = document.getElementById("follow-add");
  var followStatus = document.getElementById("follow-status");
  var followsEl = document.getElementById("follows");

  var choices = [];
  var presets = {};
  var saveTimer = null;
  var hydrating = true;
  var jobsLoaded = false;
  var followsStamp = "";
  var FOLLOW_LABELS = {
    offline: "Offline",
    live: "Live",
    checking: "Checking",
    error: "Error"
  };
  var AUDIO_HELP = {
    live: "Same audio as the player, including music. Starts from now.",
    rewind: "Rewinds to the beginning. On Twitch, this is the copy where copyrighted music is already removed."
  };
  var AUDIO_CONSEQUENCE = {
    live: "Starts from now.",
    rewind: "Starts from the beginning."
  };
  var STOPPABLE = { starting: true, downloading: true, merging: true };
  var STATE_LABELS = {
    starting: "Starting",
    downloading: "Downloading",
    merging: "Merging",
    finished: "Finished",
    error: "Error",
    interrupted: "Interrupted",
    external: "External"
  };

  function known(value) {
    return value !== null && value !== undefined && value !== "";
  }

  function setStatus(message, kind) {
    formStatus.textContent = message || "";
    if (kind) formStatus.dataset.kind = kind;
    else delete formStatus.dataset.kind;
  }

  function setSettingsNote(message, kind) {
    settingsNote.textContent = message || "";
    if (kind) settingsNote.dataset.kind = kind;
    else delete settingsNote.dataset.kind;
  }

  function syncStart() {
    startBtn.disabled = urlInput.value.trim() === "";
  }

  function syncFollowAdd() {
    followAdd.disabled = followInput.value.trim() === "";
  }

  function setFollowStatus(message, kind) {
    followStatus.textContent = message || "";
    if (kind) followStatus.dataset.kind = kind;
    else delete followStatus.dataset.kind;
  }

  function updateExactTemplate() {
    templateExact.textContent = templateInput.value;
  }

  function selectedSource() {
    var picked = document.querySelector('input[name="audio_source"]:checked');
    return picked ? picked.value : "rewind";
  }

  function setSource(source) {
    var value = AUDIO_HELP[source] ? source : "rewind";
    var input = document.querySelector('input[name="audio_source"][value="' + value + '"]');
    if (input) input.checked = true;
    audioHelp.textContent = AUDIO_HELP[value];
    if (audioConsequence) audioConsequence.textContent = AUDIO_CONSEQUENCE[value];
  }

  function renderDestinationButtons() {
    destinationChoices.replaceChildren();
    var current = destinationInput.value;
    choices.forEach(function (folder) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "choice" + (folder === current ? " is-selected" : "");
      button.textContent = folder;
      button.addEventListener("click", function () {
        destinationInput.value = folder;
        renderDestinationButtons();
        queueSave(true);
      });
      destinationChoices.appendChild(button);
    });
  }

  function renderPresetButtons() {
    templatePresets.replaceChildren();
    var current = templateInput.value;
    Object.keys(presets).forEach(function (label) {
      var value = presets[label];
      var button = document.createElement("button");
      button.type = "button";
      button.className = "choice" + (value === current ? " is-selected" : "");
      button.textContent = label;
      button.addEventListener("click", function () {
        templateInput.value = value;
        updateExactTemplate();
        renderPresetButtons();
        queueSave(true);
      });
      templatePresets.appendChild(button);
    });
  }

  function queueSave(immediate) {
    if (hydrating) return;
    clearTimeout(saveTimer);
    if (immediate) saveConfig();
    else saveTimer = setTimeout(saveConfig, 400);
  }

  async function readMessage(response) {
    var text = await response.text();
    if (!text) return "";
    try {
      var data = JSON.parse(text);
      if (data && known(data.error)) return String(data.error);
    } catch (err) {
      return text;
    }
    return text;
  }

  async function saveConfig() {
    var body = {
      destination: destinationInput.value,
      template: templateInput.value,
      audio_source: selectedSource()
    };
    try {
      var response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setSettingsNote(message || "Could not save settings.", "error");
        return;
      }
      setSettingsNote("Saved.");
    } catch (err) {
      setSettingsNote("Could not save settings.", "error");
    }
  }

  async function loadConfig() {
    hydrating = true;
    var response = await fetch("/api/config");
    if (!response.ok) throw new Error("config");
    var data = await response.json();
    destinationInput.value = known(data.destination) ? String(data.destination) : "";
    templateInput.value = known(data.template) ? String(data.template) : "";
    setSource(data.audio_source || (data.live_from_start ? "rewind" : "live"));
    choices = Array.isArray(data.destination_choices) ? data.destination_choices.map(String) : [];
    presets = data.template_presets && typeof data.template_presets === "object" ? data.template_presets : {};
    updateExactTemplate();
    renderDestinationButtons();
    renderPresetButtons();
    hydrating = false;
  }

  function formatFragment(fragment, total) {
    if (!known(fragment) && !known(total)) return "";
    if (known(fragment) && known(total)) return "fragment " + fragment + "/" + total;
    if (known(fragment)) return "fragment " + fragment;
    return "fragment —/" + total;
  }

  function formatPercent(percent) {
    if (!known(percent)) return "";
    var number = Number(percent);
    if (!Number.isFinite(number)) return String(percent);
    var rounded = Math.round(number * 10) / 10;
    return (rounded % 1 === 0 ? String(rounded) : String(rounded)) + "%";
  }

  function appendLabeled(parent, className, label, text) {
    var line = document.createElement("p");
    line.className = className;
    var name = document.createElement("span");
    name.className = "stream-label";
    name.textContent = label;
    line.appendChild(name);
    line.appendChild(document.createTextNode(text));
    parent.appendChild(line);
  }

  function streamText(stream) {
    var parts = [];
    if (known(stream.size)) parts.push(String(stream.size));
    if (known(stream.speed)) parts.push(String(stream.speed));
    var fragment = formatFragment(stream.fragment, stream.fragment_total);
    if (fragment) parts.push(fragment);
    if (known(stream.percent)) parts.push(formatPercent(stream.percent));
    return parts.length ? parts.join(" · ") : "—";
  }

  function renderJob(job) {
    var card = document.createElement("article");
    card.className = "job";

    var head = document.createElement("div");
    head.className = "job-head";

    var title = document.createElement("h3");
    title.className = "job-url";
    title.textContent = known(job.url) ? String(job.url) : "Untitled grab";

    var state = document.createElement("p");
    var stateName = known(job.state) ? String(job.state) : "unknown";
    state.className = "job-state state-" + stateName;
    state.textContent = STATE_LABELS[stateName] || stateName;

    head.append(title, state);
    card.appendChild(head);

    if (job.owner === "external") {
      var note = document.createElement("p");
      note.className = "elsewhere";
      note.textContent = "Already downloading elsewhere";
      card.appendChild(note);
    }

    var bits = [];
    if (known(job.size)) bits.push(String(job.size));
    if (known(job.speed)) bits.push(String(job.speed));
    var fragment = formatFragment(job.fragment, job.fragment_total);
    if (fragment) bits.push(fragment);
    var percent = formatPercent(job.percent);
    if (percent) bits.push(percent);
    if (bits.length) {
      var meta = document.createElement("p");
      meta.className = "job-meta";
      meta.textContent = bits.join(" · ");
      card.appendChild(meta);
    }

    if (job.video && typeof job.video === "object") {
      appendLabeled(card, "stream", "Video", streamText(job.video));
    }
    if (job.audio && typeof job.audio === "object") {
      appendLabeled(card, "stream", "Audio", streamText(job.audio));
    }

    if (stateName === "finished" && known(job.output_path)) {
      appendLabeled(card, "output", "Saved", String(job.output_path));
    }

    if (known(job.error)) {
      var error = document.createElement("p");
      error.className = "error";
      error.textContent = String(job.error);
      card.appendChild(error);
    }

    if (Array.isArray(job.log_tail) && job.log_tail.length) {
      var log = document.createElement("pre");
      log.className = "log";
      log.textContent = job.log_tail.slice(-5).join("\n");
      card.appendChild(log);
    }

    if (job.owner === "livegrab" && STOPPABLE[stateName]) {
      var stop = document.createElement("button");
      stop.type = "button";
      stop.className = "stop";
      stop.textContent = "Stop";
      stop.addEventListener("click", function () {
        stopJob(job.id, stop);
      });
      card.appendChild(stop);
    }

    return card;
  }

  async function stopJob(id, button) {
    if (!known(id)) return;
    button.disabled = true;
    button.textContent = "Stopping…";
    try {
      var response = await fetch("/api/jobs/" + encodeURIComponent(id) + "/stop", {
        method: "POST"
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setStatus(message || "Could not stop that grab.", "error");
        button.disabled = false;
        button.textContent = "Stop";
        return;
      }
      await refreshJobs();
    } catch (err) {
      setStatus("Could not stop that grab.", "error");
      button.disabled = false;
      button.textContent = "Stop";
    }
  }

  function showJobsMessage(message) {
    var empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = message;
    jobsEl.replaceChildren(empty);
  }

  async function refreshJobs() {
    var response = await fetch("/api/jobs");
    if (!response.ok) throw new Error("jobs");
    var data = await response.json();
    var jobs = Array.isArray(data.jobs) ? data.jobs.slice() : [];
    jobsLoaded = true;
    if (!jobs.length) {
      showJobsMessage("No grabs yet.");
      return;
    }
    jobs.sort(function (a, b) {
      var left = known(a.started_at) ? String(a.started_at) : "";
      var right = known(b.started_at) ? String(b.started_at) : "";
      if (left === right) return 0;
      return left < right ? 1 : -1;
    });
    var fragment = document.createDocumentFragment();
    jobs.forEach(function (job) {
      fragment.appendChild(renderJob(job));
    });
    jobsEl.replaceChildren(fragment);
  }

  function followLabel(follow) {
    if (follow.error) return "error";
    if (follow.live_status === "is_live") return "live";
    if (follow.enabled !== false && !follow.last_checked) return "checking";
    return "offline";
  }

  function renderFollows(follows) {
    if (!follows.length) {
      var empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No followed channels.";
      followsEl.replaceChildren(empty);
      return;
    }
    var fragment = document.createDocumentFragment();
    follows.forEach(function (follow) {
      fragment.appendChild(renderFollow(follow));
    });
    followsEl.replaceChildren(fragment);
  }

  function renderFollow(follow) {
    var row = document.createElement("article");
    row.className = "follow";

    var login = document.createElement("p");
    login.className = "follow-login";
    login.textContent = known(follow.login) ? String(follow.login) : "Channel";

    var label = followLabel(follow);
    var status = document.createElement("p");
    status.className = "follow-status is-" + label;
    status.textContent = FOLLOW_LABELS[label] || label;

    var enabledLabel = document.createElement("label");
    enabledLabel.className = "check";
    var toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = follow.enabled !== false;
    toggle.setAttribute("aria-label", "Enabled");
    var enabledText = document.createElement("span");
    enabledText.textContent = "Enabled";
    enabledLabel.append(toggle, enabledText);
    toggle.addEventListener("change", function () {
      setFollowEnabled(follow.login, toggle.checked, toggle);
    });

    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove";
    remove.textContent = "Remove";
    remove.addEventListener("click", function () {
      removeFollow(follow.login, remove);
    });

    row.append(login, status, enabledLabel, remove);
    return row;
  }

  async function setFollowEnabled(login, enabled, toggle) {
    if (!known(login)) return;
    toggle.disabled = true;
    try {
      var response = await fetch("/api/follows/" + encodeURIComponent(login), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: enabled })
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setFollowStatus(message || "Could not update that channel.", "error");
        toggle.checked = !enabled;
        toggle.disabled = false;
        return;
      }
      var data = await response.json();
      applyFollows(data);
      setFollowStatus(enabled ? "Channel enabled." : "Channel disabled.");
    } catch (err) {
      setFollowStatus("Could not update that channel.", "error");
      toggle.checked = !enabled;
      toggle.disabled = false;
    }
  }

  async function removeFollow(login, button) {
    if (!known(login)) return;
    button.disabled = true;
    try {
      var response = await fetch("/api/follows/" + encodeURIComponent(login), {
        method: "DELETE"
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setFollowStatus(message || "Could not remove that channel.", "error");
        button.disabled = false;
        return;
      }
      var data = await response.json();
      applyFollows(data);
      setFollowStatus("Channel removed.");
    } catch (err) {
      setFollowStatus("Could not remove that channel.", "error");
      button.disabled = false;
    }
  }

  function applyFollows(data) {
    var follows = data && Array.isArray(data.follows) ? data.follows : [];
    followsStamp = JSON.stringify(follows);
    renderFollows(follows);
  }

  function showFollowsMessage(message) {
    var empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = message;
    followsEl.replaceChildren(empty);
  }

  async function refreshFollows() {
    var response = await fetch("/api/follows");
    if (!response.ok) throw new Error("follows");
    var data = await response.json();
    var follows = Array.isArray(data.follows) ? data.follows : [];
    var stamp = JSON.stringify(follows);
    if (stamp === followsStamp) return;
    followsStamp = stamp;
    renderFollows(follows);
  }

  followForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    var channel = followInput.value.trim();
    if (!channel) {
      setFollowStatus("Enter a Twitch channel.", "error");
      followInput.focus();
      syncFollowAdd();
      return;
    }
    followAdd.disabled = true;
    try {
      var response = await fetch("/api/follows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: channel })
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setFollowStatus(message || "Could not add that channel.", "error");
        return;
      }
      var data = await response.json();
      followInput.value = "";
      applyFollows(data);
      setFollowStatus("Channel added. Livegrab checks it on the next poll.");
    } catch (err) {
      setFollowStatus("Could not add that channel.", "error");
    } finally {
      syncFollowAdd();
    }
  });

  followInput.addEventListener("input", syncFollowAdd);

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    var url = urlInput.value.trim();
    if (!url) {
      setStatus("Enter a URL before starting a grab.", "error");
      urlInput.focus();
      syncStart();
      return;
    }
    startBtn.disabled = true;
    try {
      var response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          destination: destinationInput.value,
          template: templateInput.value,
          audio_source: selectedSource()
        })
      });
      if (!response.ok) {
        var message = await readMessage(response);
        setStatus(message || "Could not start the grab.", "error");
        return;
      }
      urlInput.value = "";
      setStatus("Grab started.");
      await refreshJobs();
    } catch (err) {
      setStatus("Could not start the grab.", "error");
    } finally {
      syncStart();
    }
  });

  destinationInput.addEventListener("input", function () {
    renderDestinationButtons();
    queueSave(false);
  });

  templateInput.addEventListener("input", function () {
    updateExactTemplate();
    renderPresetButtons();
    queueSave(false);
  });

  document.querySelectorAll('input[name="audio_source"]').forEach(function (input) {
    input.addEventListener("change", function () {
      setSource(selectedSource());
      queueSave(true);
    });
  });

  urlInput.addEventListener("input", syncStart);

  async function init() {
    syncStart();
    syncFollowAdd();
    try {
      await loadConfig();
    } catch (err) {
      hydrating = false;
      setSettingsNote("Settings are not available yet.", "error");
    }
    try {
      await refreshJobs();
    } catch (err) {
      showJobsMessage("Jobs are not available yet.");
    }
    try {
      await refreshFollows();
    } catch (err) {
      showFollowsMessage("Followed channels are not available yet.");
    }
    setInterval(function () {
      refreshJobs().catch(function () {
        if (!jobsLoaded) showJobsMessage("Jobs are not available yet.");
      });
    }, 2000);
    setInterval(function () {
      refreshFollows().catch(function () {
        if (!followsStamp) showFollowsMessage("Followed channels are not available yet.");
      });
    }, 15000);
  }

  init();
})();
