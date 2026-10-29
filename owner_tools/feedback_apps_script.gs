/**
 * TubeArchive Pro - installations + ratings endpoint (Google Apps Script web app)            version 2.3.1
 *
 * One row per INSTALLATION (install_id). Columns (row 1, found by name, any order, case does not matter):
 *   install_id | installation_date | version | os | language | country | rating_date | rating | feedback | new_features
 *
 *   POST (JSON from the program)
 *     - registration (no rating): creates the row (installation_date is written only once); a new version / language
 *       / country of the same install_id just updates those cells
 *     - rating (rating 1-5): fills rating_date / rating / feedback / new_features of the row of that install_id
 *   GET ?action=stats -> {"users": 224, "versions": {"2.2.8": 3, ...}, "average": 4.6, "count": 120, "stars": {...}}
 *   GET ?action=reviews -> {"reviews": [{"rating": 5, "feedback": "...", "date": "2026-10-20 10:00:00", "country": "EG", "version": "2.3.1"}, ...]}
 *     the newest 100 rated rows (no install_id is sent); the Reviews page of the program shows them.
 *     users = number of rows (installations), versions = installations per version. The splash screen shows them.
 *
 * Any other column of yours (status, notes ...) is never touched.
 *
 * Set up / update (every time you paste a new version of this file)
 *   1. Google Sheet > Extensions > Apps Script. Replace the code with this file. Save.
 *   2. Run the function  setup  once (permission is asked the first time).
 *   3. Deploy > Manage deployments > pencil > Version: New version > Deploy.   (the /exec address stays the same)
 *      First time: Deploy > New deployment > Web app > Execute as: Me > Who has access: Anyone.
 */
var SHEET_ID = "1SVJOaa8VGKJJd3K9CGOiJhEy7pwdojuGjPkMdNVZ4YU";
var SHEET_NAME = "";                       // "" = the first tab of the sheet
var FIELDS = ["install_id", "installation_date", "version", "os", "language", "country",
              "rating_date", "rating", "feedback", "new_features"];
var TEXT_FIELDS = ["install_id", "installation_date", "version", "os", "language", "country",
                   "rating_date", "feedback", "new_features"];     // plain text: "=..." never runs
var MAX_TEXT = 2000;

function setup() { cols_(sheet_()); }

function sheet_() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = SHEET_NAME ? ss.getSheetByName(SHEET_NAME) : ss.getSheets()[0];
  if (!sh) throw new Error("sheet not found");
  return sh;
}

/** {field: column number (1-based)}; missing columns are added to the header row. */
function cols_(sh) {
  var width = Math.max(1, sh.getLastColumn());
  var head = sh.getRange(1, 1, 1, width).getValues()[0].map(function (h) { return String(h).trim().toLowerCase(); });
  var empty = head.every(function (h) { return h === ""; });
  var map = {};
  FIELDS.forEach(function (f) {
    var i = head.indexOf(f);
    if (i < 0) {
      i = empty ? FIELDS.indexOf(f) : head.length;
      while (head.length <= i) head.push("");
      head[i] = f;
      sh.getRange(1, i + 1).setValue(f).setFontWeight("bold");
    }
    map[f] = i + 1;
  });
  TEXT_FIELDS.forEach(function (f) { sh.getRange(1, map[f], sh.getMaxRows(), 1).setNumberFormat("@"); });
  return map;
}

function clean_(v, max) {
  return String(v === undefined || v === null ? "" : v)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .trim()
    .substring(0, max || MAX_TEXT);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function now_() { return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss"); }

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);
    var data = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    var id = clean_(data.install_id, 64);
    if (id.length < 16) return json_({status: "error", message: "install_id missing"});
    var rating = parseInt(data.rating, 10), hasRating = rating >= 1 && rating <= 5;

    var sh = sheet_(), c = cols_(sh), last = sh.getLastRow(), target = 0;
    if (last > 1) {
      var hit = sh.getRange(2, c.install_id, last - 1, 1).createTextFinder(id).matchEntireCell(true).findNext();
      if (hit) target = hit.getRow();
    }
    var isNew = !target;
    if (isNew) target = last + 1;
    function put(f, v) { sh.getRange(target, c[f]).setValue(v); }

    put("install_id", id);
    if (isNew || !sh.getRange(target, c.installation_date).getValue()) {
      var d = clean_(data.installation_date, 25);
      put("installation_date", /^\d{4}-\d{2}-\d{2}/.test(d) ? d : now_());
    }
    ["version", "os", "language", "country"].forEach(function (f) {
      var v = clean_(data[f], f === "os" ? 120 : 20);
      if (v) put(f, v);
    });
    if (hasRating) {
      var when = clean_(data.rating_date, 25);
      put("rating_date", /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(when) ? when : now_());
      put("rating", rating);
      put("feedback", clean_(data.feedback));
      put("new_features", clean_(data.new_features));
    }
    CacheService.getScriptCache().removeAll(["stats", "reviews"]);
    return json_({status: "success"});
  } catch (err) {
    return json_({status: "error", message: String(err)});
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

function doGet(e) {
  if (e && e.parameter && e.parameter.action === "reviews") {
    var rc = CacheService.getScriptCache();
    var rhit = rc.get("reviews");
    if (rhit) return ContentService.createTextOutput(rhit).setMimeType(ContentService.MimeType.JSON);
    var rsh = sheet_(), rcols = cols_(rsh), rlast = rsh.getLastRow(), list = [];
    if (rlast > 1) {
      rsh.getRange(2, 1, rlast - 1, rsh.getLastColumn()).getValues().forEach(function (r) {
        var v = parseInt(r[rcols.rating - 1], 10);
        if (!(v >= 1 && v <= 5)) return;
        list.push({rating: v, feedback: String(r[rcols.feedback - 1] || ""), date: String(r[rcols.rating_date - 1] || ""),
                   country: String(r[rcols.country - 1] || ""), version: String(r[rcols.version - 1] || "")});
      });
    }
    list.sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; });
    var rout = JSON.stringify({reviews: list.slice(0, 100)});
    if (rout.length < 90000) rc.put("reviews", rout, 600);
    return ContentService.createTextOutput(rout).setMimeType(ContentService.MimeType.JSON);
  }
  if (e && e.parameter && e.parameter.action === "stats") {
    var cache = CacheService.getScriptCache();
    var hit = cache.get("stats");
    if (hit) return ContentService.createTextOutput(hit).setMimeType(ContentService.MimeType.JSON);
    var sh = sheet_(), c = cols_(sh), last = sh.getLastRow();
    var stars = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}, sum = 0, n = 0, users = 0, versions = {};
    if (last > 1) {
      var vals = sh.getRange(2, 1, last - 1, sh.getLastColumn()).getValues();
      vals.forEach(function (r) {
        if (!String(r[c.install_id - 1]).trim()) return;
        users++;
        var ver = String(r[c.version - 1]).trim();
        if (ver) versions[ver] = (versions[ver] || 0) + 1;
        var v = parseInt(r[c.rating - 1], 10);
        if (v >= 1 && v <= 5) { stars[String(v)]++; sum += v; n++; }
      });
    }
    var out = JSON.stringify({users: users, versions: versions,
                              average: n ? Math.round(sum / n * 100) / 100 : 0, count: n, stars: stars});
    cache.put("stats", out, 600);
    return ContentService.createTextOutput(out).setMimeType(ContentService.MimeType.JSON);
  }
  return json_({status: "ok"});
}
