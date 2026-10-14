"""Export actual analysis artifacts into a portable, buildless report website."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent


def build_site():
    import pandas as pd
    destination = ROOT / 'site' / 'dist'
    destination.mkdir(parents=True, exist_ok=True)
    # The independent Sites checkout is ignored; a fresh GitHub clone uses docs.
    for filename in ('index.html', 'styles.css', 'app.js'):
        if not (destination / filename).exists():
            shutil.copy2(ROOT / 'docs' / filename, destination / filename)
    data = {}
    for name, title in [('startups', '50 Startups'), ('boston', 'Boston Housing')]:
        source = ROOT / 'outputs' / name
        report = json.loads((source / 'report.json').read_text(encoding='utf-8'))
        # Do not expose the local absolute source path in the website.
        report.pop('source', None)
        report['title'] = title
        report['test_predictions'] = pd.read_csv(source / 'test_predictions.csv').to_dict('records')
        report['model_predictions'] = pd.read_csv(source / 'model_comparison_predictions.csv').to_dict('records')
        report['example'] = pd.read_csv(source / 'prediction_input.csv').iloc[0].to_dict()
        data[name] = report
        assets = destination / 'assets' / name
        assets.mkdir(parents=True, exist_ok=True)
        for artifact in source.iterdir():
            if artifact.suffix in ('.png', '.csv'):
                shutil.copy2(artifact, assets / artifact.name)
        (assets / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    (destination / 'data.js').write_text('window.REPORT_DATA = ' + json.dumps(data, ensure_ascii=False, allow_nan=False) + ';\n', encoding='utf-8')
    (destination / '.nojekyll').write_text('', encoding='utf-8')
    # Keep a GitHub Pages-ready copy, with paths relative to its index.html.
    docs = ROOT / 'docs'
    shutil.copytree(destination, docs, dirs_exist_ok=True)
    print(f'Website exported to {destination} and {docs}')


if __name__ == '__main__':
    build_site()
