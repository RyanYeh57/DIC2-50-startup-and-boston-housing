'use strict';
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const fmt = (value, digits=2) => Number(value).toLocaleString('en-US', {maximumFractionDigits:digits, minimumFractionDigits:digits});
const colors = ['#635bde','#19a58f','#e49c39','#db638c','#488fce','#8263b4','#bb7652','#44a6b2','#90a241','#d45c50'];
let dataset = 'startups', count = 2, visibleModels = new Set();
const current = () => window.REPORT_DATA[dataset];
const selected = () => current().browser_feature_models.find(model => model.count === count);

// Dependency-free SVG charts remain available offline and when opened as a file.
function chart(element, series, options={}) {
  const all = series.flatMap(item => item.points).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (!all.length) { element.innerHTML = '<div class="chart-empty">請選取至少一個模型</div>'; return; }
  const width=options.wide ? 1080 : 520, height=options.wide ? 390 : 270;
  const margin={left:76,right:20,top:16,bottom:49};
  let xmin=Math.min(...all.map(p=>p.x)), xmax=Math.max(...all.map(p=>p.x));
  let ymin=Math.min(...all.map(p=>p.y)), ymax=Math.max(...all.map(p=>p.y));
  if (options.zero) {ymin=Math.min(ymin,0);ymax=Math.max(ymax,0);}
  if (xmin===xmax) {xmin-=1;xmax+=1;}
  const padding=(ymax-ymin || 1)*0.12; ymin-=padding; ymax+=padding;
  const sx=x=>margin.left+(x-xmin)/(xmax-xmin)*(width-margin.left-margin.right);
  const sy=y=>height-margin.bottom-(y-ymin)/(ymax-ymin)*(height-margin.top-margin.bottom);
  let markup=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHTML(options.label || '分析圖表')}">`;
  const tick = value => Math.abs(value)>=10000 ? `${(value/1000).toFixed(0)}k` : Math.abs(value)>=100 ? value.toFixed(0) : value.toFixed(options.precision ?? 2);
  for(let i=0;i<=4;i++) {
    const value=ymin+(ymax-ymin)*i/4, y=sy(value);
    markup+=`<line x1="${margin.left}" y1="${y}" x2="${width-margin.right}" y2="${y}" stroke="#edf0f6"/><text x="${margin.left-10}" y="${y+4}" text-anchor="end" fill="#8b97a8" font-size="10">${tick(value)}</text>`;
  }
  const xvalues = options.counts ? [...new Set(all.map(p=>p.x))].sort((a,b)=>a-b) : Array.from({length:6},(_,i)=>xmin+(xmax-xmin)*i/5);
  for(const value of xvalues) markup+=`<text x="${sx(value)}" y="${height-margin.bottom+21}" text-anchor="middle" fill="#8b97a8" font-size="10">${options.counts ? value : tick(value)}</text>`;
  if (options.zero) markup+=`<line x1="${margin.left}" y1="${sy(0)}" x2="${width-margin.right}" y2="${sy(0)}" stroke="#b2bbcb" stroke-dasharray="4 4"/>`;
  if (options.diagonal) markup+=`<path d="M${sx(xmin)} ${sy(xmin)} L${sx(xmax)} ${sy(xmax)}" stroke="#b5bdcc" stroke-dasharray="5 4" fill="none"/>`;
  for(const item of series) {
    const points=item.points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
    if(item.line!==false) markup+=`<path d="${points.map((p,i)=>`${i?'L':'M'}${sx(p.x)} ${sy(p.y)}`).join(' ')}" fill="none" stroke="${item.color}" stroke-width="${options.wide?1.9:2.6}"/>`;
    if(item.dots!==false) for(const p of points) markup+=`<circle class="svg-point" cx="${sx(p.x)}" cy="${sy(p.y)}" r="${options.wide?3:4}" fill="${item.color}" stroke="white" stroke-width="1.2" ${options.counts?`data-count="${p.x}" tabindex="0" role="button" aria-label="選取 ${p.x} 個特徵"`:''}><title>${escapeHTML(item.name)} · ${options.xlabel || 'x'}: ${fmt(p.x)} · ${fmt(p.y,4)}</title></circle>`;
  }
  if(options.counts) {
    const p=series[0].points.find(p=>p.x===count);
    if(p) markup+=`<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="8" fill="none" stroke="${series[0].color}" stroke-width="2"/>`;
  }
  markup+=`<text x="${(width+margin.left)/2}" y="${height-7}" text-anchor="middle" fill="#7a879c" font-size="10">${escapeHTML(options.xlabel || '')}</text><text x="14" y="${height/2}" transform="rotate(-90 14 ${height/2})" text-anchor="middle" fill="#7a879c" font-size="10">${escapeHTML(options.ylabel || '')}</text></svg>`;
  element.innerHTML=markup;
  if(options.counts) for(const point of element.querySelectorAll('[data-count]')) {
    const choose=()=>{ count=Number(point.dataset.count); renderFeatures(); };
    point.addEventListener('click', choose);
    point.addEventListener('keydown', e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});
  }
}

function renderFeatures() {
  const data=current(), model=selected();
  $('feature-buttons').innerHTML=data.browser_feature_models.map(m=>`<button data-count="${m.count}" class="${m.count===count?'active':''}" aria-pressed="${m.count===count}">k = ${m.count}</button>`).join('');
  $('feature-buttons').querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{count=Number(button.dataset.count);renderFeatures();}));
  $('selected-features').innerHTML=model.features.map(feature=>`<span class="feature-chip">${escapeHTML(feature)}</span>`).join('');
  chart($('rmse-chart'), [{name:'Test RMSE',color:colors[0],points:data.browser_feature_models.map(m=>({x:m.count,y:m.metrics.RMSE}))}], {label:'RMSE by Number of Features',counts:true,xlabel:'Number of Features'});
  chart($('r2-chart'), [{name:'Test R²',color:colors[1],points:data.browser_feature_models.map(m=>({x:m.count,y:m.metrics.R2}))}], {label:'R-squared by Number of Features',counts:true,xlabel:'Number of Features',precision:3});
  $('selection-summary').innerHTML=`<span>目前選擇 <strong>${count}</strong> 個編碼後特徵</span><span>Test RMSE <strong>${fmt(model.metrics.RMSE)}</strong>　 R² <strong>${fmt(model.metrics.R2,4)}</strong>　 MAE <strong>${fmt(model.metrics.MAE)}</strong></span>`;
  $('coefficients').innerHTML=`<tr><td>Intercept</td><td>${fmt(model.intercept,4)}</td></tr>`+model.features.map((feature,i)=>`<tr><td>${escapeHTML(feature)}</td><td>${fmt(model.coefficients[i],6)}</td></tr>`).join('');
  predict();
}

function renderInputs() {
  const data=current(), prep=data.browser_preprocessing;
  $('predictor-inputs').innerHTML=prep.numeric.map((field,i)=>`<label>${escapeHTML(field)}<input type="number" step="any" required name="${escapeHTML(field)}" id="input-${i}" value="${Number(data.example[field]).toFixed(4)}"></label>`).join('')+prep.categorical.map(field=>`<label>${escapeHTML(field)}<select name="${escapeHTML(field)}">${prep.categories[field].map(value=>`<option value="${escapeHTML(value)}" ${value===data.example[field]?'selected':''}>${escapeHTML(value)}</option>`).join('')}</select></label>`).join('');
  $('prediction-label').textContent=dataset==='startups'?'預測 Profit':'預測 MEDV（原始資料單位）';
}

function predict() {
  const model=selected(), prep=current().browser_preprocessing, form=$('predictor');
  if (!model || !form.elements.length) return;
  const encoded={};
  for(const field of prep.numeric) {
    const value=form.elements.namedItem(field).value;
    if(value.trim()==='' || !Number.isFinite(Number(value))) { $('prediction-value').textContent='請輸入完整數值';return; }
    encoded[field]=Number(value);
  }
  for(const field of prep.categorical) for(const category of prep.categories[field].slice(1)) encoded[`${field}_${category}`]=form.elements.namedItem(field).value===category?1:0;
  const prediction=model.intercept+model.features.reduce((sum,feature,i)=>sum+encoded[feature]*model.coefficients[i],0);
  $('prediction-value').textContent=Number.isFinite(prediction)?fmt(prediction):'輸入無效';
}

function renderModels() {
  const data=current(), rows=data.model_predictions, xname=dataset==='startups'?'R&D Spend':'RM';
  const ordered=[...rows].sort((a,b)=>a.x-b.x), models=data.model_comparison;
  $('model-legend').innerHTML=`<span class="muted" style="padding:5px 9px">● Actual Data</span>`+models.map((model,i)=>`<button data-model="${escapeHTML(model.Model)}" aria-pressed="${visibleModels.has(model.Model)}"><span class="dot" style="background:${colors[i]}"></span>${escapeHTML(model.Model)}</button>`).join('');
  $('model-legend').querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{const label=button.dataset.model;if(visibleModels.has(label))visibleModels.delete(label);else visibleModels.add(label);renderModels();}));
  const series=models.flatMap((model,i)=>visibleModels.has(model.Model)?[{name:model.Model,color:colors[i],dots:false,points:ordered.map(row=>({x:row.x,y:row[model.Model]}))}]:[]);
  series.push({name:'Actual Data',color:'#223047',line:false,points:ordered.map(row=>({x:row.x,y:row.actual}))});
  chart($('model-chart'),series,{wide:true,label:'Comparison of Different Regression Models',xlabel:xname,ylabel:dataset==='startups'?'Profit':'MEDV'});
  $('model-chart-note').textContent=`橫軸：${xname}；縱軸：${dataset==='startups'?'Profit':'MEDV'}。各模型使用全部輸入欄位（特徵選取／PCA 配置除外）；折線連接依橫軸排序的測試預測，並非單一變數的反應曲線。`;
  $('model-table').innerHTML=models.map((row,i)=>`<tr><td><span class="rank ${i===0?'first':''}">${String(i+1).padStart(2,'0')}</span></td><td>${escapeHTML(row.Model)}</td><td>${fmt(row.MSE)}</td><td>${fmt(row.RMSE,4)}</td><td>${fmt(row['R2 Score'],4)}</td></tr>`).join('');
}

function render() {
  const data=current(), metrics=data.test_metrics;
  document.querySelectorAll('[data-dataset]').forEach(button=>{button.classList.toggle('active',button.dataset.dataset===dataset);button.setAttribute('aria-pressed',String(button.dataset.dataset===dataset));});
  $('hero-title').textContent=data.title+' / '+(dataset==='startups'?'Profit Prediction':'Housing Regression');
  $('hero-description').textContent=dataset==='startups'?'研發、行政、行銷支出與州別，能解釋多少公司利潤？用特徵數量比較、十種迴歸模型與即時預測，探索這份 50 筆資料的訊息。':'以 13 個輸入欄位預測歷史資料中的 MEDV。比較不同特徵數與模型，觀察預測誤差，理解線性模型與非線性模型的差異。';
  $('rows-tag').textContent=`${data.usable_rows} observations · ${data.train_rows} train / ${data.test_rows} test`;
  $('target-tag').textContent=dataset==='startups'?'Target: Profit':'Target: MEDV';
  const cards=[['R-SQUARED',fmt(metrics.R2,4),'Test set · explained variance','↗'],['RMSE',fmt(metrics.RMSE),'Test set · original target units','∿'],['MAE',fmt(metrics.MAE),'Test set · mean absolute error','±'],['CV RMSE',fmt(data.training_cv_RMSE_mean),`5 folds · ± ${fmt(data.training_cv_RMSE_std)}`,'▤']];
  $('metrics').innerHTML=cards.map(([label,value,sub,icon])=>`<article class="metric"><span>${label}</span><span class="metric-icon">${icon}</span><strong>${value}</strong><small>${sub}</small></article>`).join('');
  for(const [id,file] of [['feature-download','feature_comparison.csv'],['model-download','model_comparison.csv'],['prediction-download','test_predictions.csv'],['report-download','report.json']]) $(id).href=`assets/${dataset}/${file}`;
  renderInputs();renderFeatures();renderModels();
  chart($('actual-chart'),[{name:'Test observation',color:colors[0],line:false,points:data.test_predictions.map(row=>({x:row.actual,y:row.predicted}))}],{label:'Actual vs Predicted',xlabel:'Actual target',diagonal:true});
  chart($('residual-chart'),[{name:'Test residual',color:colors[1],line:false,points:data.test_predictions.map(row=>({x:row.predicted,y:row.residual}))}],{label:'Residuals vs Predicted',xlabel:'Predicted target',zero:true});
  const steps=[['Business Understanding',dataset==='startups'?'使用支出與州別預測 Profit，探索企業投入與利潤的關係。':'以 Boston Housing 的歷史輸入欄位預測 MEDV，作為迴歸教學分析。'],['Data Understanding',`${data.original_rows} 筆原始紀錄，${data.duplicate_rows} 筆完全重複。檢查欄位、缺失值與描述統計。`],['Data Preparation','清除缺失目標與重複紀錄。先切分再擬合中位數／眾數填補與 One-Hot 編碼。'],['Modeling','完整 Pipeline、多元線性迴歸、五折交叉驗證，另比較十種模型配置。'],['Evaluation',`Test RMSE ${fmt(metrics.RMSE)}；平均值基準 ${fmt(data.baseline_test_metrics.RMSE)}。本次${data.meets_exploratory_criterion?'優於':'未優於'}基準。`],['Deployment','保存完整模型，再次載入並驗證預測一致。網頁即時預測使用匯出的線性模型係數。']];
  $('workflow-steps').innerHTML=steps.map(([title,body],i)=>`<article class="workflow-step"><span class="step-number">0${i+1}</span><h3>${title}</h3><p>${body}</p></article>`).join('');
  document.title=`${data.title} · DIC2 Regression Explorer`;
}

document.querySelectorAll('[data-dataset]').forEach(button=>button.addEventListener('click',()=>{dataset=button.dataset.dataset;count=Math.min(2,current().browser_feature_models.length);visibleModels=new Set(current().model_comparison.map(row=>row.Model));render();}));
$('predictor').addEventListener('submit',event=>{event.preventDefault();predict();});
$('predictor').addEventListener('input',predict);
visibleModels=new Set(current().model_comparison.map(row=>row.Model));
render();
