(() => {
  const dataNode = document.getElementById('chart-data');
  if (dataNode && window.Plotly) {
    const charts = JSON.parse(dataNode.textContent);
    const shared = {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: {family: 'DM Sans, sans-serif', color: '#52665a', size: 11},
      margin: {l: 48, r: 20, t: 52, b: 48},
      title: {font: {family: 'Manrope, sans-serif', size: 14, color: '#34483a'}, x: 0.04, xanchor: 'left'},
      xaxis: {gridcolor: '#edf2ed', zerolinecolor: '#e3ebe3'},
      yaxis: {gridcolor: '#edf2ed', zerolinecolor: '#e3ebe3'},
      legend: {orientation: 'h', y: -0.18, font: {size: 10}},
    };
    const ids = {daily: 'chart-daily', costs: 'chart-costs', products: 'chart-products', channels: 'chart-channels', vendors: 'chart-vendors', marginProduct: 'chart-margin-product'};
    Object.entries(ids).forEach(([key, id]) => {
      const node = document.getElementById(id);
      if (node && charts[key]) Plotly.newPlot(node, charts[key].data, {...shared, ...charts[key].layout}, {responsive: true, displayModeBar: false});
    });
  }

  document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(item => item.classList.toggle('active', item === button));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.toggle('active', panel.id === `tab-${button.dataset.tab}`));
    if (window.Plotly) window.dispatchEvent(new Event('resize'));
  }));

  const fixed = document.getElementById('fixed-cost');
  const price = document.getElementById('sale-price');
  const variable = document.getElementById('variable-cost');
  const unitsResult = document.getElementById('bep-units');
  const revenueResult = document.getElementById('bep-revenue');
  const rupiah = value => `Rp ${Math.round(value).toLocaleString('id-ID')}`;
  function updateBep() {
    if (!fixed || !price || !variable || !unitsResult || !revenueResult) return;
    const contribution = Number(price.value) - Number(variable.value);
    if (contribution <= 0) { unitsResult.textContent = 'Periksa harga & biaya'; revenueResult.textContent = 'Harga harus lebih besar dari biaya variabel.'; return; }
    const units = Math.ceil(Number(fixed.value) / contribution);
    unitsResult.textContent = `${units.toLocaleString('id-ID')} unit`;
    revenueResult.textContent = `BEP omzet: ${rupiah(units * Number(price.value))}`;
  }
  [fixed, price, variable].forEach(input => input && input.addEventListener('input', updateBep));
  updateBep();
})();
