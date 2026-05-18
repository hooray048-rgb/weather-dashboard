let allWeatherData = [];

const TEAMS = [
    { name: '수도권서부팀', locations: ['파주 물류', '부천 물류', '남양주 물류', '인천 물류'] },
    { name: '수도권동부팀', locations: ['진위 물류', '군포 물류', '이천 물류', '원주 물류', '강릉 물류'] },
    { name: '지방권서부팀', locations: ['대전 물류', '광주 물류', '전주 물류', '진천 물류', '아산 물류', '순천 물류', '목포 물류'] },
    { name: '지방권중부팀', locations: ['대구 물류', '안동 물류', '경주 물류'] },
    { name: '지방권남부팀', locations: ['부산 물류', '창원 물류', '진주 물류', '제주 물류'] },
];

// API 호출 함수
async function fetchWeatherData(url) {
    const loading = document.getElementById('loadingSpinner');
    const error = document.getElementById('errorMessage');
    const container = document.getElementById('weatherContainer');

    loading.style.display = 'block';
    error.classList.remove('show');
    container.innerHTML = '';

    try {
        const response = await fetch(url);

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || `HTTP Error: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (err) {
        showError(err.message);
        return null;
    } finally {
        loading.style.display = 'none';
    }
}

// 모든 날씨 데이터 로드
async function loadAllWeather() {
    const data = await fetchWeatherData('/api/weather/all');

    if (data && data.success) {
        allWeatherData = data.data;
        displayWeatherCards(allWeatherData);
    }
}

// 특정 거점 검색
async function searchLocation() {
    const searchInput = document.getElementById('searchInput');
    const locationName = searchInput.value.trim();

    if (!locationName) {
        showError('거점 이름을 입력해주세요');
        return;
    }

    const data = await fetchWeatherData(`/api/weather/${encodeURIComponent(locationName)}`);

    if (data && data.success) {
        displayWeatherCards([data.data]);
    }
}

// 엔터키로 검색
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchLocation();
    }
});

// 날씨 카드 표시 (팀별 그룹핑)
function displayWeatherCards(weatherData) {
    const container = document.getElementById('weatherContainer');

    if (!weatherData || weatherData.length === 0) {
        container.innerHTML = '<p class="no-data">검색 결과가 없습니다</p>';
        return;
    }

    const dataByName = {};
    weatherData.forEach(item => {
        const name = item.location?.name;
        if (name) dataByName[name] = item;
    });

    // 팀별로 데이터가 있는 경우 팀 섹션으로 표시
    const hasTeamData = TEAMS.some(team =>
        team.locations.some(loc => dataByName[loc])
    );

    if (hasTeamData) {
        container.innerHTML = TEAMS.map(team => {
            const teamItems = team.locations
                .map(loc => dataByName[loc])
                .filter(Boolean);

            if (teamItems.length === 0) return '';

            return `
                <div class="team-section">
                    <h2 class="team-title">${team.name}</h2>
                    <div class="team-cards">
                        ${teamItems.map(item => createWeatherCard(item)).join('')}
                    </div>
                </div>
            `;
        }).join('');
    } else {
        container.innerHTML = weatherData.map(item => createWeatherCard(item)).join('');
    }
}

// 날씨 카드 생성
function createWeatherCard(item) {
    const location = item.location || {};
    const weather = item.weather || {};
    const condition = weather.condition || '정보 없음';
    const precipitation = weather.precipitation || 0;
    const rawData = item.raw_data || {};

    const avgTemp = weather.temperature !== 'N/A' ? weather.temperature : null;
    const maxTemp = rawData.max_temp != null ? rawData.max_temp : null;
    const minTemp = rawData.min_temp != null ? rawData.min_temp : null;
    const maxPerceived = rawData.max_perceived != null ? rawData.max_perceived : null;
    const minPerceived = rawData.min_perceived != null ? rawData.min_perceived : null;

    const statusClass = getStatusClass(condition);
    const statusText = getStatusText(condition);

    const displayTemp = avgTemp != null ? avgTemp : (maxTemp != null ? maxTemp : 'N/A');
    const tempRangeHtml = (maxTemp != null && minTemp != null)
        ? `<div class="temp-range">최고 ${maxTemp}° / 최저 ${minTemp}°</div>`
        : '';

    let perceivedHtml = '';
    if (maxPerceived != null) {
        perceivedHtml = `
            <div class="weather-info-row">
                <span class="weather-label">체감 최고</span>
                <span class="weather-value perceived-hot">${maxPerceived}°</span>
            </div>`;
    } else if (minPerceived != null) {
        perceivedHtml = `
            <div class="weather-info-row">
                <span class="weather-label">체감 최저</span>
                <span class="weather-value perceived-cold">${minPerceived}°</span>
            </div>`;
    }

    return `
        <div class="weather-card">
            <div class="card-header">
                <div class="location-name">${location.name || '알 수 없는 거점'}</div>
                <div class="weather-status status-${statusClass}">${statusText}</div>
            </div>

            <div class="temp-section">
                <div class="temperature">${displayTemp}<span style="font-size:1.1rem;font-weight:500;color:#94A8BC;">°</span></div>
                <div class="temp-detail">
                    ${tempRangeHtml}
                    <div class="weather-condition">${condition}</div>
                </div>
            </div>

            <div class="weather-info">
                <div class="weather-info-row">
                    <span class="weather-label">강수량</span>
                    <span class="weather-value">${precipitation}mm</span>
                </div>
                ${perceivedHtml}
                ${rawData.alerts && rawData.alerts.length > 0 ? `
                <div class="weather-alerts">
                    ${rawData.alerts.map(alert => `<div class="alert-item">${alert}</div>`).join('')}
                </div>
                ` : ''}
            </div>
        </div>
    `;
}

// 상태 클래스 결정
function getStatusClass(condition) {
    if (condition.includes('맑')) return 'clear';
    if (condition.includes('눈')) return 'snow';
    if (condition.includes('비') || condition.includes('강수')) return 'rain';
    return 'cloud';
}

// 상태 텍스트 결정
function getStatusText(condition) {
    if (condition.includes('맑')) return '맑음';
    if (condition.includes('눈')) return '눈';
    if (condition.includes('비') || condition.includes('강수')) return '강수';
    return '흐림';
}

// 필터 적용
function applyFilters() {
    if (!allWeatherData || allWeatherData.length === 0) {
        return;
    }

    const filterClear = document.getElementById('filterClear').checked;
    const filterRain = document.getElementById('filterRain').checked;

    let filtered = allWeatherData;

    if (filterClear) {
        filtered = filtered.filter(item => {
            const condition = item.weather?.condition || '';
            return condition.includes('맑') || condition.includes('맑음');
        });
    }

    if (filterRain) {
        filtered = filtered.filter(item => {
            const condition = item.weather?.condition || '';
            return condition.includes('비') || condition.includes('강수');
        });
    }

    displayWeatherCards(filtered);
}

// 에러 메시지 표시
function showError(message) {
    const error = document.getElementById('errorMessage');
    error.textContent = message;
    error.classList.add('show');
}

// 페이지 로드 시 자동으로 모든 날씨 정보 불러오기
document.addEventListener('DOMContentLoaded', () => {
    console.log('날씨 정보 앱 로드됨');
    loadAllWeather();
});
