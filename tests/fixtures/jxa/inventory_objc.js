// JXA end-to-end fixture: Foundation bridge, app automation, closures,
// classes, error handling and Unicode. Only compiled by the tests, never run.
ObjC.import('Foundation');
ObjC.import('AppKit');

const app = Application.currentApplication();
app.includeStandardAdditions = true;

const CSV = `sku,category,qty,price
A-100, tools ,3,4.50
B-200,garden,2,19.99
C-300,kitchen,5,3.10 — “café” ✓`;

class Logger {
  constructor(prefix) { this.prefix = prefix; this.lines = []; }
  add(msg) { this.lines.push(`${this.prefix}: ${msg}`); return this.lines.length; }
  dump() { return this.lines.join('\n'); }
}

function trimmed(s) {
  const ws = $.NSCharacterSet.whitespaceAndNewlineCharacterSet;
  return ObjC.unwrap($(s).stringByTrimmingCharactersInSet(ws));
}

function makeCounter(start, step) {
  let current = start;
  return () => (current += step);
}

function parse(text, log) {
  const rows = [];
  text.split('\n').slice(1).forEach((line, i) => {
    try {
      const [sku, category, qty, price] = line.split(',').map(trimmed);
      if (!price) throw new Error(`line ${i + 2}: missing price`);
      rows.push({ sku, category: category.toLowerCase(), qty: +qty, price: parseFloat(price) });
    } catch (e) {
      log.add(`skip ${e.message}`);
    }
  });
  return rows;
}

function run(argv) {
  const log = new Logger('report');
  const rows = parse(CSV, log);
  const totals = $.NSMutableDictionary.dictionary;
  for (const r of rows) {
    const prev = ObjC.unwrap(totals.objectForKey(r.category)) || 0;
    totals.setObjectForKey(prev + r.qty * r.price, r.category);
  }
  const next = makeCounter(10, 5);
  const keys = ObjC.deepUnwrap(totals.allKeys).sort();
  keys.forEach(k => log.add(`${k}=${ObjC.unwrap(totals.objectForKey(k)).toFixed(2)} #${next()}`));

  const finder = Application('Finder');
  const disks = finder.disks.whose({ name: { _not: '' } }).name();
  const clip = $.NSPasteboard.generalPasteboard.stringForType($.NSPasteboardTypeString);
  const re = $.NSRegularExpression.regularExpressionWithPatternOptionsError('\\d+', 0, null);
  log.add(`disks=${disks.length} clip=${clip.isNil() ? '' : ObjC.unwrap(clip).length} re=${re.numberOfCaptureGroups}`);
  app.doShellScript('echo done > /tmp/jxa_fixture.txt');
  return log.dump();
}
