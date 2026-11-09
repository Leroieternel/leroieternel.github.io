/* Real paper aggregates, rendered locally with Chart.js. No analytics or remote runtime. */
(() => {
  'use strict';
  if (!window.Chart) return; // Keep the original figures when the library is unavailable.
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const activeCharts = [];
  // Also resize charts outside the viewport when the page crosses a grid breakpoint.
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => activeCharts.forEach(c => {
      const p=c.canvas.parentElement;c.resize(p.clientWidth,p.clientHeight);
    }),120);
  });
  const patterns = [[], [7, 3], [3, 3], [2, 3], [8, 3, 2, 3], [2, 2], [6, 3]];
  const points = ['circle', 'rect', 'triangle', 'rectRot', 'triangle', 'cross', 'crossRot'];
  const make = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const comma = n => n.toLocaleString('en-US');
  Chart.defaults.font.family = '"Noto Sans", sans-serif';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#677584';

  // Preserve the source figure's sample standard deviations on the bar charts.
  const errorBars = {
    id: 'paperErrorBars',
    afterDatasetsDraw(chart) {
      if (chart.config.type !== 'bar') return;
      const {ctx, scales: {y}, chartArea: a} = chart;
      ctx.save(); ctx.beginPath(); ctx.rect(a.left, a.top, a.right-a.left, a.bottom-a.top); ctx.clip();
      chart.data.datasets.forEach((ds, i) => {
        if (!ds.errors || !chart.isDatasetVisible(i)) return;
        chart.getDatasetMeta(i).data.forEach((bar, j) => {
          const val = ds.data[j], sd = ds.errors[j];
          if (!Number.isFinite(val) || !Number.isFinite(sd)) return;
          const x = bar.x, hi = y.getPixelForValue(val+sd), lo = y.getPixelForValue(val-sd);
          ctx.strokeStyle = '#455867'; ctx.lineWidth = 1.15;
          ctx.beginPath(); ctx.moveTo(x,hi); ctx.lineTo(x,lo);
          ctx.moveTo(x-3,hi); ctx.lineTo(x+3,hi); ctx.moveTo(x-3,lo); ctx.lineTo(x+3,lo); ctx.stroke();
        });
      });
      ctx.restore();
    }
  };
  Chart.register(errorBars);

  const baseOptions = () => ({
    responsive: true, maintainAspectRatio: false,
    animation: reduceMotion ? false : {duration: 280},
    interaction: {mode: 'index', intersect: false},
    plugins: {legend: {display: false}, tooltip: {
      backgroundColor: 'rgba(30, 43, 55, .96)', padding: 12, cornerRadius: 8,
      titleFont: {size: 13, weight: '600'}, bodyFont: {size: 12}, bodySpacing: 5,
      usePointStyle: true,
      callbacks: {label: c => `${c.dataset.label}: ${Number(c.raw).toFixed(3)}`}
    }}
  });
  const axes = (min, max, title) => ({
    x: {grid: {display: false}, border: {color: '#dfe5eb'}, ticks: {maxRotation: 0}},
    y: {min, max, title: {display: true, text: title}, border: {display: false},
      grid: {color: '#edf1f4'}, ticks: {maxTicksLimit: 6}}
  });
  function card(grid, title, cls) {
    const box = make('div', `chart-card ${cls || ''}`), id = `chart-${grid.dataset.group}-${grid.children.length}`;
    const heading = make('h4', '', title); heading.id = `${id}-title`;
    const surface = make('div', 'chart-surface'), canvas = make('canvas'); canvas.id = id;
    canvas.setAttribute('role','img'); canvas.setAttribute('aria-labelledby',heading.id);
    canvas.setAttribute('aria-describedby',`${grid.dataset.group}-chart-help`); canvas.tabIndex = 0;
    canvas.append(document.createTextNode(title));
    surface.append(canvas); box.append(heading,surface); grid.append(box);
    return {canvas,box};
  }
  function keyboard(chart, status) {
    let index = 0, series = 0;
    chart.canvas.addEventListener('keydown', e => {
      if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','Escape'].includes(e.key)) return;
      e.preventDefault();
      if (e.key === 'Escape') { chart.tooltip.setActiveElements([], {x:0,y:0}); chart.update('none'); return; }
      const visible = chart.data.datasets.map((_,i) => i).filter(i => chart.isDatasetVisible(i));
      if (!visible.length) return;
      if (e.key==='ArrowUp') series--;
      if (e.key==='ArrowDown') series++;
      series = (series + visible.length) % visible.length;
      const dsIndex = visible[series], ds = chart.data.datasets[dsIndex];
      if (e.key==='ArrowLeft') index--;
      if (e.key==='ArrowRight') index++;
      if (e.key==='Home') index=0;
      if (e.key==='End') index=ds.data.length-1;
      index=(index+ds.data.length)%ds.data.length;
      const el=chart.getDatasetMeta(dsIndex).data[index];
      chart.setActiveElements([{datasetIndex:dsIndex,index}]);
      chart.tooltip.setActiveElements([{datasetIndex:dsIndex,index}],el.getCenterPoint());
      chart.update('none');
      const ctx={dataset:ds,dataIndex:index,raw:ds.data[index],parsed:chart.getDatasetMeta(dsIndex)._parsed[index],label:chart.data.labels[index]};
      const label=chart.options.plugins.tooltip.callbacks.label(ctx);
      status.textContent=`${chart.canvas.getAttribute('aria-label') || ''} ${ctx.label}. ${[].concat(label).join('. ')}`;
    });
    chart.canvas.addEventListener('blur', () => { chart.setActiveElements([]);chart.tooltip.setActiveElements([],{x:0,y:0});chart.update('none'); });
  }
  function legend(host, models, charts) {
    const legend = make('div','chart-legend'); legend.setAttribute('role','group');legend.setAttribute('aria-label','Toggle models');
    models.forEach((m,i) => {
      const btn=make('button'); btn.type='button';btn.dataset.model=m.id;btn.setAttribute('aria-pressed','true');
      const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 26 12');svg.setAttribute('aria-hidden','true');
      const line=document.createElementNS(svg.namespaceURI,'path');line.setAttribute('d','M1 6H25');line.setAttribute('stroke',m.color);line.setAttribute('stroke-width',String(m.borderWidth ?? 3));line.setAttribute('stroke-dasharray',(m.borderDash ?? patterns[i%patterns.length]).join(' '));svg.append(line);
      if(m.pointBackgroundColor) {
        const point=document.createElementNS(svg.namespaceURI,'circle');
        point.setAttribute('cx','13');point.setAttribute('cy','6');point.setAttribute('r','3');
        point.setAttribute('fill',m.pointBackgroundColor);point.setAttribute('stroke',m.color);point.setAttribute('stroke-width','2');svg.append(point);
      }
      btn.append(svg,document.createTextNode(m.label));
      btn.addEventListener('click',() => {
        const show=btn.getAttribute('aria-pressed')!=='true';btn.setAttribute('aria-pressed',String(show));
        charts.forEach(c => {const n=c.data.datasets.findIndex(d=>d.model===m.id);if(n>=0){c.setDatasetVisibility(n,show);c.update();}});
      });legend.append(btn);
    });host.append(legend);
  }
  function dataTable(host, headers, rows) {
    const details=make('details','chart-data'),summary=make('summary','','View data');details.append(summary);
    const wrap=make('div','chart-table-scroll'),table=make('table'),head=make('thead'),tr=make('tr');
    table.append(make('caption','', 'Values used in these charts'));
    headers.forEach(h=>{const th=make('th','',h);th.scope='col';tr.append(th);});head.append(tr);table.append(head);
    const body=make('tbody');rows.forEach(row=>{const tr=make('tr');row.forEach(v=>tr.append(make('td','',String(v))));body.append(tr);});table.append(body);wrap.append(table);details.append(wrap);
    host.append(details);
  }
  function render(root, data) {
    const kind=root.dataset.chartGroup, host=root.querySelector('.interactive-content'), charts=[];
    const help=make('p','chart-sr-only','Use left and right arrow keys to inspect points, up and down to change model, and Escape to close the tooltip.');help.id=`${kind}-chart-help`;host.append(help);
    const status=make('p','chart-sr-only');status.setAttribute('aria-live','polite');host.append(status);
    const grid=make('div',`chart-grid ${kind}-grid`);grid.dataset.group=kind;
    // Canvas sizes must be measurable before Chart.js initializes them.
    host.hidden=false;
    try {
      if (kind==='sources') {
        let mode='episodes';
        const toolbar=make('div','chart-toolbar');host.append(toolbar);
        const controls=make('div','chart-segments');controls.setAttribute('role','group');controls.setAttribute('aria-label','Dataset measure');toolbar.prepend(controls);
        host.append(grid);
        const a=card(grid,'Episodes by source','sources'), b=card(grid,'Share by source','pie');
        const labels=data.sources.map(s=>s.name),colors=data.sources.map(s=>s.color);
        const total=make('p','chart-total');b.box.append(total);
        const tooltip={label:c=>{
          const n=c.raw;return `${comma(n)} ${mode} · ${(100*n/data.totals[mode]).toFixed(2)}% of all ${mode}`;
        }};
        const opts=baseOptions();opts.indexAxis='y';opts.interaction={mode:'nearest',intersect:true};opts.plugins.tooltip.callbacks=tooltip;
        opts.scales={x:{beginAtZero:true,title:{display:true,text:'Episodes'},grid:{color:'#edf1f4'},border:{display:false},ticks:{maxTicksLimit:5}},y:{grid:{display:false},border:{display:false},ticks:{font:{size:11}}}};
        charts.push(new Chart(a.canvas,{type:'bar',data:{labels,datasets:[{label:'Episodes',data:data.sources.map(s=>s.episodes),backgroundColor:colors,borderRadius:3,maxBarThickness:18}]},options:opts}));
        const pieOpts=baseOptions();pieOpts.interaction={mode:'nearest',intersect:true};pieOpts.plugins.tooltip.callbacks=tooltip;pieOpts.layout={padding:12};
        charts.push(new Chart(b.canvas,{type:'pie',data:{labels,datasets:[{label:'Episodes',data:data.sources.map(s=>s.episodes),backgroundColor:colors,borderWidth:1,borderColor:'#fff',hoverOffset:9}]},options:pieOpts}));
        function setMode(next) {
          mode=next;const name=next[0].toUpperCase()+next.slice(1);
          controls.querySelectorAll('button').forEach(btn=>btn.setAttribute('aria-pressed',String(btn.dataset.mode===next)));
          a.box.querySelector('h4').textContent=`${name} by source`;total.replaceChildren(make('strong','',comma(data.totals[mode])),document.createTextNode(mode));
          charts.forEach(c=>{c.data.datasets[0].data=data.sources.map(s=>s[mode]);c.data.datasets[0].label=name;c.canvas.setAttribute('aria-label',`${name} by source`);if(c.config.type==='bar')c.options.scales.x.title.text=name;c.update();});
        }
        ['episodes','actions','missions'].forEach(mode=>{const btn=make('button','',mode[0].toUpperCase()+mode.slice(1));btn.type='button';btn.dataset.mode=mode;btn.addEventListener('click',()=>setMode(mode));controls.append(btn);});
        setMode(mode);
        dataTable(host,['Source','Episodes','Actions','Missions'],data.sources.map(s=>[s.name,s.episodes,s.actions,s.missions]));
      } else {
        const models=kind==='realworld'?data.realworldModels:data.models.map(m=>{
          const styled=m.id==='robobrain25_8b_nv'
            ? {...m,color:'#6476AD',borderWidth:2,borderDash:[6,4],pointStyle:'circle',pointBackgroundColor:'#ffffff'}
            : m;
          return kind==='radar'?{...styled,borderDash:[]}:styled;
        });
        legend(host,models,charts);host.append(grid);
        const panels=kind==='progress'?data.progress:kind==='radar'?data.radars:data.realworld;
        panels.forEach(panel=>{
          const a=card(grid,panel.title,kind==='radar'?'radar':kind==='realworld'?'bars':'line');
          a.canvas.setAttribute('aria-label',panel.title);
          const opts=baseOptions();let type,labels;
          if(kind==='progress') {
            type='line';labels=data.cutoffs;
            opts.scales=axes(panel.metric==='SBERT'?.2:.5,1,`${panel.metric} similarity ↑`);
            opts.scales.x={type:'linear',min:0,max:95,title:{display:true,text:'Observed action progress (%)'},grid:{display:false},ticks:{stepSize:25}};
            opts.plugins.tooltip.callbacks={title:items=>`Action progress: ${items[0].parsed.x}%`,label:c=>`${c.dataset.label}: ${c.parsed.y.toFixed(3)}`};
          } else if(kind==='radar') {
            type='radar';labels=data.radarAxes;
            opts.interaction={mode:'nearest',intersect:false};
            opts.scales={r:{min:0,max:1,ticks:{stepSize:.2,backdropColor:'transparent',font:{size:10}},pointLabels:{font:{size:11},color:'#485c6c'},angleLines:{color:'#e2e9ee'},grid:{color:'#dbe4ec'}}};
            opts.plugins.tooltip.callbacks={label:c=>`${c.dataset.label}: ${c.dataIndex>=4?(Number(c.raw)*100).toFixed(2)+'%':Number(c.raw).toFixed(3)}`};
          } else {
            type='bar';labels=data.tasks;opts.interaction={mode:'nearest',intersect:true};
            opts.scales=axes(0,panel.metric==='teleop_s'?70:6,panel.metric==='teleop_s'?'Teleoperation time (s) ↓':'Time per request (s) ↓');
            opts.plugins.tooltip.callbacks={label:c=>{const r=c.dataset.stats[c.dataIndex];return [`${c.dataset.label}: ${r.mean.toFixed(3)} s`,`SD: ±${r.sd.toFixed(3)} s`,r.n===null?'Reported aggregate':`n = ${r.n} ${r.unit}`];}};
          }
          const datasets=models.filter(m=>panel.series[m.id]).map(m=>{
            const i=models.indexOf(m),values=panel.series[m.id];
            if(kind==='realworld') {
              return {model:m.id,label:m.label,data:values.map(v=>v.mean),errors:values.map(v=>v.sd),stats:values,backgroundColor:m.color+'CC',borderColor:m.color,borderWidth:1,borderRadius:3,maxBarThickness:32};
            }
            return {model:m.id,label:m.label,data:kind==='progress'?values.map((y,j)=>({x:data.cutoffs[j],y})):values,
              borderColor:m.color,backgroundColor:m.color+(kind==='radar'?'10':'FF'),borderWidth:m.borderWidth ?? (m.id==='tuned'?3:1.7),
              borderDash:m.borderDash ?? patterns[i],pointStyle:m.pointStyle ?? points[i],pointBackgroundColor:m.pointBackgroundColor,pointRadius:kind==='radar'?2.5:3,pointHoverRadius:6,pointHitRadius:14,
              fill:kind==='radar',tension:0,order:m.id==='tuned'?0:1};
          });
          charts.push(new Chart(a.canvas,{type,data:{labels,datasets},options:opts}));
        });
      }
      charts.forEach(c=>keyboard(c,status));
      activeCharts.push(...charts);
      root.classList.add('charts-ready');
    } catch(error) {
      charts.forEach(c=>c.destroy());host.replaceChildren();host.hidden=true;
      console.error('Chart rendering failed; original figure retained.', error);
    }
  }
  fetch(new URL('../data/charts.json?v=20261107-1',document.currentScript.src)).then(r=>{
    if(!r.ok)throw new Error('Chart data unavailable');return r.json();
  }).then(async data=>{
    await document.fonts.ready;
    document.querySelectorAll('[data-chart-group]').forEach(root=>render(root,data));
  }).catch(error=>console.error('Chart data unavailable; original figures retained.',error));
})();
