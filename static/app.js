document.addEventListener("DOMContentLoaded", () => {
    fetchTickers();

    document.getElementById("analyze-input").addEventListener("input", (e) => {
        const term = e.target.value.trim().toUpperCase();
        const items = document.querySelectorAll("#ticker-list li");
        items.forEach(li => {
            if (li.textContent.toUpperCase().includes(term)) {
                li.style.display = "flex";
            } else {
                li.style.display = "none";
            }
        });
    });

    document.getElementById("btn-analyze-all").addEventListener("click", () => {
        if (confirm("Tüm BIST100 hisseleri için arka planda tarama başlatılacak. Bu işlem uzun sürebilir. Onaylıyor musunuz?")) {
            triggerAnalysisAll();
        }
    });

    // Progress Polling
    setInterval(async () => {
        try {
            const res = await fetch("/api/progress");
            const progress = await res.json();
            
            const container = document.getElementById("progress-container");
            if (progress.is_running) {
                container.classList.remove("hidden");
                const percentage = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
                
                document.getElementById("progress-text").textContent = `Tarama: %${percentage}`;
                document.getElementById("progress-stats").textContent = `${progress.completed} / ${progress.total}`;
                document.getElementById("progress-bar-fill").style.width = `${percentage}%`;
                document.getElementById("progress-current").textContent = `${progress.current_ticker} analiz ediliyor...`;
            } else {
                if (!container.classList.contains("hidden")) {
                    if (progress.total > 0 && progress.completed > 0) {
                        document.getElementById("progress-text").textContent = "Tamamlandı!";
                        document.getElementById("progress-bar-fill").style.width = "100%";
                        document.getElementById("progress-current").textContent = `Başarılı: ${progress.successful}, Hata: ${progress.failed}`;
                        setTimeout(() => {
                            container.classList.add("hidden");
                            fetchTickers();
                        }, 5000);
                    } else {
                        container.classList.add("hidden");
                    }
                }
            }
        } catch (e) {
            // Sessizce hatayı yut
        }
    }, 2000);
});

async function fetchTickers() {
    try {
        const res = await fetch("/api/tickers");
        const data = await res.json();
        const list = document.getElementById("ticker-list");
        list.innerHTML = "";
        
        data.tickers.forEach(ticker => {
            const li = document.createElement("li");
            li.textContent = ticker;
            li.addEventListener("click", () => loadHistory(ticker, li));
            list.appendChild(li);
        });
    } catch (err) {
        showToast("Hisseler yüklenirken hata oluştu.");
    }
}

let currentHistory = [];
let currentAnalysisItem = null;

async function loadHistory(ticker, liElement) {
    // Aktif stili ayarla
    document.querySelectorAll("#ticker-list li").forEach(el => el.classList.remove("active"));
    if (liElement) liElement.classList.add("active");

    document.getElementById("welcome-state").classList.add("hidden");
    const dashboard = document.getElementById("analysis-dashboard");
    dashboard.classList.remove("hidden");
    
    document.getElementById("selected-ticker-title").textContent = `${ticker} Analiz Raporu`;
    
    const btnReanalyze = document.getElementById("btn-reanalyze");
    btnReanalyze.classList.remove("hidden");
    btnReanalyze.onclick = () => {
        triggerAnalysis(ticker);
    };

    try {
        const res = await fetch(`/api/history/${ticker}`);
        const data = await res.json();
        
        if (data.history && data.history.length > 0) {
            currentHistory = data.history;
            currentAnalysisItem = data.history[0];
            updateDashboard(currentAnalysisItem);
            updateTimeline(currentHistory, currentAnalysisItem);
            loadPriceChart(ticker);
        } else {
            showToast("Bu hisseye ait kayıtlı analiz bulunamadı.");
        }
    } catch (err) {
        showToast("Veriler yüklenirken hata oluştu.");
    }
}

let priceChartInstance = null;

async function loadPriceChart(ticker) {
    try {
        const res = await fetch(`/api/chart/${ticker}`);
        const data = await res.json();
        
        const ctx = document.getElementById('price-chart').getContext('2d');
        
        if (priceChartInstance) {
            priceChartInstance.destroy();
        }

        if (!data.dates || data.dates.length === 0) {
            showToast("Grafik verisi bulunamadı.");
            return;
        }

        priceChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: `${ticker} Son 6 Aylık Kapanış Fiyatı (₺)`,
                    data: data.prices,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#f8fafc' }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', maxTicksLimit: 10 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    } catch (e) {
        showToast("Grafik yüklenirken hata oluştu.");
    }
}

function updateDashboard(data) {
    document.getElementById("val-timestamp").textContent = new Date(data.timestamp).toLocaleString("tr-TR");

    if (!data.is_successful) {
        document.getElementById("val-signal").textContent = "HATA";
        document.getElementById("val-signal").className = "value signal-kacin";
        document.getElementById("val-risk").textContent = "-";
        document.getElementById("val-price").textContent = "-";
        document.getElementById("val-pe").textContent = "-";
        document.getElementById("val-pb").textContent = "-";
        document.getElementById("val-roe").textContent = "-";
        document.getElementById("val-commentary").textContent = data.error_message || "Bilinmeyen bir hata oluştu.";
        return;
    }

    const sig = document.getElementById("val-signal");
    sig.textContent = data.signal;
    sig.className = "value";
    if (data.signal.includes("AL")) sig.classList.add("signal-al");
    else if (data.signal.includes("TUT")) sig.classList.add("signal-tut");
    else if (data.signal.includes("KAÇIN")) sig.classList.add("signal-kacin");

    document.getElementById("val-risk").textContent = `${data.risk_score} / 100`;
    document.getElementById("val-price").textContent = `${data.price.toFixed(2)} ₺`;
    document.getElementById("val-pe").textContent = data.pe_ratio === 999.9 ? "N/A" : data.pe_ratio.toFixed(2);
    document.getElementById("val-pb").textContent = data.pb_ratio === 999.9 ? "N/A" : data.pb_ratio.toFixed(2);
    document.getElementById("val-roe").textContent = `%${(data.roe * 100).toFixed(2)}`;
    
    document.getElementById("val-commentary").textContent = data.commentary;
    document.getElementById("val-timestamp").textContent = new Date(data.timestamp).toLocaleString("tr-TR");
}

function updateTimeline(history, currentItem) {
    const tl = document.getElementById("history-timeline");
    tl.innerHTML = "";
    
    history.forEach((item) => {
        const li = document.createElement("li");
        li.style.alignItems = "center";
        const date = new Date(item.timestamp).toLocaleString("tr-TR");
        const signalColor = item.signal.includes("AL") ? "var(--signal-al)" : (item.signal.includes("KAÇIN") ? "var(--signal-kacin)" : "var(--signal-tut)");
        
        li.innerHTML = `
            <div>
                <span>${date}</span>
                <span style="color: ${item.is_successful ? signalColor : 'var(--signal-kacin)'}; margin-left: 15px; font-weight: 600;">
                    ${item.is_successful ? item.signal : 'HATA'}
                </span>
            </div>
        `;
        
        if (!currentItem || item.timestamp !== currentItem.timestamp) {
            const btn = document.createElement("button");
            btn.textContent = "Detayları Gör";
            btn.className = "btn-detail";
            btn.onclick = () => {
                currentAnalysisItem = item;
                updateDashboard(item);
                updateTimeline(currentHistory, currentAnalysisItem);
            };
            li.appendChild(btn);
        } else {
            const span = document.createElement("span");
            span.textContent = "Görüntüleniyor";
            span.style.fontSize = "0.75rem";
            span.style.color = "var(--accent-color)";
            span.style.fontWeight = "600";
            li.appendChild(span);
        }
        
        tl.appendChild(li);
    });
}

async function triggerAnalysisAll() {
    showToast("Tüm BIST100 taraması arka planda başlatıldı...");
    try {
        await fetch("/api/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({tickers: []})
        });
        setTimeout(fetchTickers, 3000);
    } catch (e) {
        showToast("Tarama başlatılamadı.");
    }
}

async function triggerAnalysis(ticker) {
    showToast(`${ticker} için analiz arka planda başlatıldı...`);
    try {
        await fetch("/api/analyze", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({tickers: [ticker]})
        });
        
        // Inputu temizle
        document.getElementById("analyze-input").value = "";
        
        // Birkaç saniye sonra listeyi yenile
        setTimeout(fetchTickers, 3000);
    } catch (e) {
        showToast("Analiz tetiklenemedi.");
    }
}

function showToast(msg) {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.classList.remove("hidden");
    
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}
