"""Export actual analysis artifacts into a portable, buildless report website."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent


def build_site():
    import pandas as pd
    destination = ROOT / 'site' / 'dist'
    destination.mkdir(parents=True, exist_ok=True)
    # Tracked docs templates are authoritative, including in a fresh clone.
    for filename in ('index.html', 'styles.css', 'app.js'):
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
        summary = pd.read_csv(source / 'data_summary.csv', index_col=0)
        report['input_ranges'] = {}
        for field in report['browser_preprocessing']['numeric']:
            minimum = float(summary.loc['min', field])
            maximum = float(summary.loc['max', field])
            span = maximum - minimum
            step = 1 if field in ('CHAS', 'RAD', 'TAX') else 0.0001 if span < 1 else 0.01
            report['input_ranges'][field] = {'min': minimum, 'max': maximum, 'step': step}
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
