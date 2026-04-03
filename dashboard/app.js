(function () {
  "use strict";

  var container = document.getElementById("probes");
  var lastUpdated = document.getElementById("last-updated");

  function relativeTime(iso) {
    var diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return Math.round(diff) + "s ago";
    if (diff < 3600) return Math.round(diff / 60) + "m ago";
    if (diff < 86400) return Math.round(diff / 3600) + "h ago";
    return Math.round(diff / 86400) + "d ago";
  }

  function badge(status) {
    var cls = status === "ok" ? "badge-ok" : status === "fail" ? "badge-fail" : "badge-unknown";
    var label = status === "ok" ? "Reachable" : status === "fail" ? "Blocked" : "Unknown";
    return '<span class="badge ' + cls + '">' + label + "</span>";
  }

  function renderCard(probe) {
    var dcEntries = Object.keys(probe.direct || {}).sort();
    var dcOk = 0;
    var dcTotal = dcEntries.length;

    var dcCells = dcEntries
      .map(function (key) {
        var r = probe.direct[key];
        if (r.status === "ok") dcOk++;
        var cls = r.status === "ok" ? "ok" : "fail";
        var label = key.toUpperCase();
        var ms = r.latency_ms != null ? r.latency_ms + "ms" : "-";
        return '<div class="dc-cell ' + cls + '">' + label + "<br>" + ms + "</div>";
      })
      .join("");

    var directStatus = dcOk === dcTotal ? "ok" : dcOk === 0 ? "fail" : "partial";
    var directBadge = directStatus === "ok" ? badge("ok") : badge("fail");

    var proxyHtml = "";
    if (probe.proxy) {
      var p = probe.proxy;
      var pOk = p.get_me === true;
      var pCls = pOk ? "ok" : "fail";
      var pLabel = pOk ? "Connected" : "Failed";
      var pDetail = pOk ? p.total_ms + "ms" : p.error || "unknown error";
      proxyHtml =
        '<div class="proxy-status ' + pCls + '">' +
        "Proxy (" + (p.transport || "fake-tls") + "): " +
        "<strong>" + pLabel + "</strong> &mdash; " + pDetail +
        "</div>";
    }

    return (
      '<div class="card">' +
      "<h2>" + escapeHtml(probe.region) + " " + directBadge + "</h2>" +
      '<div class="dc-grid">' + dcCells + "</div>" +
      proxyHtml +
      '<div class="meta">Last checked: ' + relativeTime(probe.timestamp) + "</div>" +
      "</div>"
    );
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  async function loadProbes() {
    try {
      var indexResp = await fetch("data/index.json");
      if (!indexResp.ok) throw new Error("No data yet");
      var probeIds = await indexResp.json();

      var probes = await Promise.all(
        probeIds.map(function (id) {
          return fetch("data/latest/" + id + ".json").then(function (r) {
            return r.ok ? r.json() : null;
          });
        })
      );

      probes = probes.filter(Boolean);

      if (probes.length === 0) {
        container.innerHTML = '<div class="loading">No probe data available yet. Probes run hourly.</div>';
        return;
      }

      probes.sort(function (a, b) {
        return a.region.localeCompare(b.region);
      });

      container.innerHTML = probes.map(renderCard).join("");

      var latest = probes.reduce(function (a, b) {
        return new Date(a.timestamp) > new Date(b.timestamp) ? a : b;
      });
      lastUpdated.textContent = "Last updated: " + relativeTime(latest.timestamp);
    } catch (e) {
      container.innerHTML =
        '<div class="loading">No probe data available yet. Probes run hourly &mdash; check back soon.</div>';
    }
  }

  loadProbes();
  setInterval(loadProbes, 60000);
})();
