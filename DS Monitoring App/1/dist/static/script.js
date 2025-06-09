// script.js - Main frontend logic for index.html
// v8.7: Added "Create MRF" button to project rows, linking to mrf_form.html with project details.
// v8.6: Added current month highlighting in updateDashboardMetrics.
// v8.5: Modified updateDashboardMetrics to handle monthly forecast/invoiced data & percentage.
// v8: Implemented console.groupCollapsed for cleaner logs, fixed initialization order error, used corrected API endpoints.
// v7: Corrected USER_INFO_API and LOGOUT_API constants and logout method to match backend routes (Option 1).
// v6: Changed logout method to GET as a common alternative (User MUST verify with backend). Added comments for API endpoint verification.
// v5: Updated logout redirect to point to login.html
// v4: Added user info fetching and logout functionality.
// v3: Changed setupCollapsibleSections to use data-target instead of aria-controls
// v2: Modified setupCollapsibleSections to use aria-controls instead of data-target (Reverted in v3)
// v1: Removed duplicate declaration of FORECAST_TOGGLE_API (it's defined in forecast.js)

// --- Constants ---
const API_BASE_URL = '/api'; // Base URL for all API calls
const PROJECTS_API = `${API_BASE_URL}/projects`;
const COMPLETED_PROJECTS_API = `${API_BASE_URL}/projects/completed`;
const DASHBOARD_API = `${API_BASE_URL}/dashboard`;
const UPDATES_LOG_API = `${API_BASE_URL}/updates/log`;
const UPLOAD_CSV_API = `${PROJECTS_API}/upload`;
const BULK_PROJECTS_API = `${PROJECTS_API}/bulk`;
const ADD_FORECAST_API = `${API_BASE_URL}/forecast`;
const FORECAST_API = `${API_BASE_URL}/forecast`;

const USER_INFO_API = `${API_BASE_URL}/user/profile`;
const LOGOUT_API = `${API_BASE_URL}/logout`;

const UPDATE_PROJECT_API = (projectId) => `${PROJECTS_API}/${projectId}`;
const PROJECT_UPDATES_API = (projectId) => `${PROJECTS_API}/${projectId}/updates`;
const UPDATE_SINGLE_API = (updateId) => `${API_BASE_URL}/updates/${updateId}`;
const UPDATE_TOGGLE_API = (updateId) => `${UPDATE_SINGLE_API(updateId)}/complete`;

// --- Global State ---
let currentProjectsData = [];
let currentCompletedProjectsData = [];
let currentSort = { key: 'remaining_amount', direction: 'desc' };
let currentlyEditingCell = null;

// --- Utility Functions FIRST ---
function getElement(id) {
    const element = document.getElementById(id);
    return element;
}

function displayFeedback(message, type = 'info') {
    console.groupCollapsed(`UI: Display Feedback (${type})`);
    console.log("Message:", message);
    const feedbackDiv = getElement('feedbackMessage');
    if (!feedbackDiv) {
        console.warn("Feedback div ('feedbackMessage') not found, falling back to console log.");
        console.log(`${type.toUpperCase()}: ${message}`);
        console.groupEnd();
        return;
    }
    feedbackDiv.textContent = message;
    const typeClasses = {
        success: 'feedback-success',
        error: 'feedback-error',
        info: 'feedback-info',
        warning: 'feedback-warning'
    };
    feedbackDiv.className = `feedback ${typeClasses[type] || typeClasses['info']} p-3 rounded border mb-4`;
    feedbackDiv.style.display = 'block';
    console.log("Feedback displayed.");
    setTimeout(() => {
        if (feedbackDiv.textContent === message) {
            clearFeedback();
        }
    }, 7000);
    console.groupEnd();
}

function clearFeedback() {
    const feedbackDiv = getElement('feedbackMessage');
    if (feedbackDiv) {
        feedbackDiv.textContent = '';
        feedbackDiv.style.display = 'none';
        feedbackDiv.className = 'feedback';
    }
}

function safe_int(value, fallback = null) {
    if (value === null || value === undefined || String(value).trim() === '') {
        return fallback;
    }
    const num = parseInt(String(value).trim(), 10);
    return isNaN(num) ? fallback : num;
}

function safeFloat(value, fallback = NaN) {
    if (value === null || value === undefined) return fallback;
    const strValue = String(value).replace(/[$,₱%]/g, '').replace(/,/g, '').trim();
    if (strValue === '') return fallback;
    const num = parseFloat(strValue);
    return isNaN(num) ? fallback : num;
}

function formatCurrency(value, fallback = 'N/A') {
    const numVal = safeFloat(value);
    if (isNaN(numVal)) return fallback;
    try {
        return new Intl.NumberFormat('en-PH', {
            style: 'currency',
            currency: 'PHP',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(numVal);
    } catch (e) {
        console.error("Currency formatting error:", e);
        return `₱${numVal.toFixed(2)}`;
    }
}

function formatPercent(value, fallback = 'N/A') {
    const numVal = safeFloat(value);
    if (isNaN(numVal)) return fallback;
    return `${numVal.toFixed(1)}%`;
}

function parseDate(dateStr) {
    if (!dateStr) return null;
    let date = null;
    try {
        if (dateStr instanceof Date && !isNaN(dateStr.getTime())) {
            return new Date(Date.UTC(dateStr.getFullYear(), dateStr.getMonth(), dateStr.getDate()));
        }
        const strInput = String(dateStr).trim();
        if (!strInput) return null;
        const isoMatch = strInput.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (isoMatch) {
            const year = parseInt(isoMatch[1], 10), month = parseInt(isoMatch[2], 10), day = parseInt(isoMatch[3], 10);
            if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
                date = new Date(Date.UTC(year, month - 1, day));
                if (!isNaN(date.getTime()) && date.getUTCFullYear() === year && (date.getUTCMonth() + 1) === month && date.getUTCDate() === day) {
                    return date;
                }
            }
        }
        const slashMatch = strInput.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
        if (slashMatch) {
            const year = parseInt(slashMatch[3], 10), month = parseInt(slashMatch[1], 10), day = parseInt(slashMatch[2], 10);
            if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
                date = new Date(Date.UTC(year, month - 1, day));
                if (!isNaN(date.getTime()) && date.getUTCFullYear() === year && (date.getUTCMonth() + 1) === month && date.getUTCDate() === day) {
                    return date;
                }
            }
        }
        date = new Date(strInput);
        if (!isNaN(date.getTime())) {
            const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
            if (!isNaN(utcDate.getTime())) return utcDate;
        }
    } catch (e) {
        console.error("Error parsing date:", dateStr, e);
    }
    return null;
}

function formatDate(dateStr, fallback = 'N/A') {
    if (!dateStr) return fallback;
    try {
        const date = parseDate(dateStr);
        return date ? `${String(date.getUTCMonth() + 1).padStart(2, '0')}/${String(date.getUTCDate()).padStart(2, '0')}/${date.getUTCFullYear()}` : fallback;
    } catch (e) {
        console.error("Error formatting date:", dateStr, e);
        return fallback;
    }
}

function formatCsvCell(value) {
    const stringValue = value === null || value === undefined ? '' : String(value);
    if (/[",\n]/.test(stringValue)) {
        const escapedValue = stringValue.replace(/"/g, '""');
        return `"${escapedValue}"`;
    }
    return stringValue;
}

async function apiFetch(url, options = {}) {
    const method = options.method || 'GET';
    console.groupCollapsed(`🌐 API Fetch: ${method} ${url}`);
    const startTime = performance.now();
    const defaultHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
    const token = localStorage.getItem('authToken');
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
        console.log("    - Authorization header added.");
    } else {
        console.log("    - No auth token found in localStorage.");
    }
    const config = { ...options, headers: { ...defaultHeaders, ...(options.headers || {}) } };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
        config.body = JSON.stringify(config.body);
        console.log("    - Request body stringified.");
    } else if (config.body instanceof FormData) {
        delete config.headers['Content-Type'];
        console.log("    - Request body is FormData, Content-Type handled by browser.");
    } else {
        console.log("    - No request body or body is not an object/FormData.");
    }
    console.log("    - Fetch config:", config);
    try {
        const response = await fetch(url, config);
        const duration = performance.now() - startTime;
        console.log(`    - Response received: Status ${response.status} (${response.statusText}) in ${duration.toFixed(0)}ms`);
        if (response.status === 401) {
            console.warn(`[apiFetch] Unauthorized access to ${url}. Redirecting to login.`);
            localStorage.removeItem('authToken');
            window.location.href = 'login.html';
            console.groupEnd();
            throw new Error('Unauthorized');
        }
        if (response.status === 204) {
            console.log("    - Success (204 No Content).");
            console.groupEnd();
            return { message: "Operation successful (No Content)." };
        }
        const contentType = response.headers.get("content-type");
        let responseData;
        try {
            if (contentType?.includes("application/json")) {
                responseData = await response.json();
                console.log("    - Parsed JSON response:", responseData);
            } else {
                const text = await response.text();
                console.log("    - Received non-JSON response (text):", text.substring(0, 200) + (text.length > 200 ? '...' : ''));
                if (!response.ok) {
                    throw new Error(text || `HTTP Error ${response.status}`);
                }
                responseData = { message: `OK (${response.status})`, data: text };
            }
        } catch (bodyError) {
            console.error(`    - Error reading/parsing body (Status: ${response.status}):`, bodyError);
            if (!response.ok) {
                throw new Error(`HTTP Error ${response.status}, failed to read/parse body.`);
            }
            responseData = { message: `OK (${response.status}), but error reading/parsing body.` };
        }
        if (!response.ok) {
            const errorMessage = responseData?.error || responseData?.message || `HTTP Error ${response.status}`;
            const error = new Error(errorMessage);
            error.data = responseData;
            error.status = response.status;
            console.error(`    - API Error ${response.status}:`, error);
            throw error;
        }
        console.log("    - Fetch successful.");
        return responseData;
    } catch (error) {
        const duration = performance.now() - startTime;
        if (error.message !== 'Unauthorized') {
            console.error(`[apiFetch] Fetch Error (${method} ${url}) after ${duration.toFixed(0)}ms:`, error);
        }
        if (!error.status && !error.data && error.message !== 'Unauthorized') {
            throw new Error(`Network error or cannot connect to API at ${url}. Ensure the backend server is running and accessible.`);
        }
        throw error;
    } finally {
        console.groupEnd();
    }
}

// --- API Calls ---
async function fetchDashboardData() {
    console.groupCollapsed("API: Fetching Dashboard Data");
    const dashboardLoadingEl = getElement('dashboardLoading');
    const dashboardErrorEl = getElement('dashboardError');
    if (dashboardLoadingEl) dashboardLoadingEl.style.display = 'block';
    if (dashboardErrorEl) dashboardErrorEl.textContent = '';
    try {
        const data = await apiFetch(DASHBOARD_API);
        console.log("    - Dashboard data received:", data);
        updateDashboardMetrics(data?.metrics || data);
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Failed to fetch dashboard data:", error);
            if (dashboardErrorEl) dashboardErrorEl.textContent = `Error: ${error.message}`;
            updateDashboardMetrics({});
        }
    } finally {
        if (dashboardLoadingEl) dashboardLoadingEl.style.display = 'none';
        console.groupEnd();
    }
}

async function fetchActiveProjects() {
    console.groupCollapsed("API: Fetching Active Projects");
    const activeProjectsLoadingEl = getElement('activeProjectsLoading');
    const activeProjectsErrorEl = getElement('activeProjectsError');
    const activeProjectsTableBody = getElement('activeProjectsTableBody');
    if (activeProjectsLoadingEl) activeProjectsLoadingEl.style.display = 'block';
    if (activeProjectsErrorEl) activeProjectsErrorEl.textContent = '';
    if (activeProjectsTableBody) activeProjectsTableBody.innerHTML = '<tr class="loading"><td colspan="12" class="text-center p-4 text-gray-500 dark:text-slate-400">Loading projects...</td></tr>';
    try {
        const data = await apiFetch(PROJECTS_API);
        currentProjectsData = data || [];
        console.log(`    - Received ${currentProjectsData.length} active projects.`);
        applyFiltersAndRender();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Failed to fetch active projects:", error);
            currentProjectsData = [];
            if (activeProjectsErrorEl) activeProjectsErrorEl.textContent = `Error: ${error.message}`;
            if (activeProjectsTableBody) activeProjectsTableBody.innerHTML = `<tr class="error"><td colspan="12">Failed to load projects: ${error.message}</td></tr>`;
        }
    } finally {
        if (activeProjectsLoadingEl) activeProjectsLoadingEl.style.display = 'none';
        console.groupEnd();
    }
}

async function fetchCompletedProjects() {
    console.groupCollapsed("API: Fetching Completed Projects");
    const completedProjectsLoadingEl = getElement('completedProjectsLoading');
    const completedProjectsErrorEl = getElement('completedProjectsError');
    const completedProjectsTableBody = getElement('completedProjectsTableBody');
    if (completedProjectsLoadingEl) completedProjectsLoadingEl.style.display = 'block';
    if (completedProjectsErrorEl) completedProjectsErrorEl.textContent = '';
    if (completedProjectsTableBody) completedProjectsTableBody.innerHTML = '<tr class="loading"><td colspan="12" class="text-center p-4 text-gray-500 dark:text-slate-400">Loading completed projects...</td></tr>';
    try {
        const data = await apiFetch(COMPLETED_PROJECTS_API);
        currentCompletedProjectsData = data || [];
        console.log(`    - Received ${currentCompletedProjectsData.length} completed projects.`);
        renderCompletedTable();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Failed to fetch completed projects:", error);
            currentCompletedProjectsData = [];
            if (completedProjectsErrorEl) completedProjectsErrorEl.textContent = `Error: ${error.message}`;
            if (completedProjectsTableBody) completedProjectsTableBody.innerHTML = `<tr class="error"><td colspan="12">Failed to load completed projects: ${error.message}</td></tr>`;
        }
    } finally {
        if (completedProjectsLoadingEl) completedProjectsLoadingEl.style.display = 'none';
        console.groupEnd();
    }
}

async function fetchProjectUpdates(projectId) {
    console.groupCollapsed(`API: Fetching Updates for Project ${projectId}`);
    const projectUpdatesList = getElement('projectUpdatesList');
    const updatesLoading = getElement('updatesLoading');
    const updatesError = getElement('updatesError');
    if (!projectUpdatesList || !updatesLoading || !updatesError) {
        console.warn("    - Missing elements required for fetching/displaying updates.");
        console.groupEnd();
        return [];
    }
    projectUpdatesList.innerHTML = '';
    updatesLoading.style.display = 'block';
    updatesError.textContent = '';
    let updates = [];
    try {
        updates = await apiFetch(PROJECT_UPDATES_API(projectId));
        updates = updates || [];
        console.log(`    - Received ${updates.length} updates.`);
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error(`    - Failed to fetch updates for project ${projectId}:`, error);
            updatesError.textContent = `Error loading updates: ${error.message}`;
        }
        updates = [];
    } finally {
        updatesLoading.style.display = 'none';
        console.groupEnd();
    }
    return updates;
}

async function fetchUserInfo() {
    console.groupCollapsed("API: Fetching User Info");
    const userDisplayNameEl = getElement('user-display-name');
    if (!userDisplayNameEl) {
        console.warn("    - User display element ('user-display-name') not found.");
        console.groupEnd();
        return;
    }
    try {
        const userInfo = await apiFetch(USER_INFO_API);
        const userName = userInfo?.username || 'User';
        const userRole = userInfo?.role || 'Guest';
        userDisplayNameEl.textContent = `${userName} (${userRole})`;
        console.log("    - User info fetched:", userInfo);
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Failed to fetch user info:", error);
            userDisplayNameEl.textContent = 'Guest';
        }
    } finally {
        console.groupEnd();
    }
}

async function handleLogout() {
    console.groupCollapsed("AUTH: Handle Logout");
    if (!confirm('Are you sure you want to logout?')) {
        console.log("    - Logout cancelled by user.");
        console.groupEnd();
        return;
    }
    displayFeedback('Logging out...', 'info');
    const logoutBtn = getElement('logout-btn');
    if (logoutBtn) logoutBtn.disabled = true;
    try {
        console.log(`    - Calling logout API: POST ${LOGOUT_API}`);
        await apiFetch(LOGOUT_API, { method: 'POST' });
        console.log("    - Logout API call successful (or 204). Clearing client-side auth...");
        localStorage.removeItem('authToken');
        console.log("    - Auth token removed from localStorage.");
        displayFeedback('Logout successful. Redirecting...', 'success');
        setTimeout(() => {
            console.log("    - Redirecting to login.html");
            window.location.href = 'login.html';
        }, 1500);
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Logout failed:", error);
            let errorMsg = `Logout failed: ${error.message}`;
            if (error.status === 405) {
                errorMsg = `Logout failed: Method not allowed for ${LOGOUT_API}. Backend expects POST.`;
            }
            displayFeedback(errorMsg, 'error');
            if (logoutBtn) logoutBtn.disabled = false;
        }
    } finally {
        console.groupEnd();
    }
}

// --- Rendering ---
function updateDashboardMetrics(data = {}) {
    console.groupCollapsed("UI: Updating Dashboard Metrics (with Monthly)");
    console.log("  - Data received:", data);
    const metricTotalRemainingEl = getElement('metricTotalRemaining');
    const metricCompletedCountEl = getElement('metricCompletedCount');
    const metricActiveCountEl = getElement('metricActiveCount');
    const metricNewCountEl = getElement('metricNewCount');
    const completedLabel = getElement('metricCompletedLabel');
    if (metricTotalRemainingEl) metricTotalRemainingEl.textContent = formatCurrency(data.total_remaining ?? 0, '₱0.00');
    if (metricCompletedCountEl) metricCompletedCountEl.textContent = data.completed_this_year_count ?? 0;
    if (metricActiveCountEl) metricActiveCountEl.textContent = data.total_active_projects_count ?? 0;
    if (metricNewCountEl) metricNewCountEl.textContent = data.new_projects_count ?? 0;
    if (completedLabel) {
        const currentYear = new Date().getFullYear();
        completedLabel.textContent = `Completed (${currentYear})`;
    }
    console.log("  - Updated overall metrics (Remaining, Counts).");
    const monthlyInvoiced = data.monthly_actual_invoiced || {};
    const monthlyForecast = data.monthly_total_forecast || {};
    const months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    const currentMonthIndex = new Date().getMonth();
    console.log("  - Updating monthly forecast/invoiced values...");
    months.forEach((monthAbbr, index) => {
        const monthNumber = index + 1;
        const isCurrentMonth = index === currentMonthIndex;
        const monthBlockEl = getElement(`metric-month-block-${monthAbbr}`);
        const forecastEl = getElement(`metric-forecast-${monthAbbr}`);
        const invoicedEl = getElement(`metric-invoiced-${monthAbbr}`);
        const percentageEl = getElement(`metric-percentage-${monthAbbr}`);
        const forecastValue = monthlyForecast[monthNumber] ?? 0.0;
        const invoicedValue = monthlyInvoiced[monthNumber] ?? 0.0;
        let percentageText = '(-%)';
        if (forecastValue > 0) {
            const percentage = (invoicedValue / forecastValue) * 100;
            percentageText = `(${percentage.toFixed(0)}%)`;
        } else if (invoicedValue > 0) {
            percentageText = '(Inf%)';
        }
        if (forecastEl) {
            forecastEl.textContent = `(Fcst: ${formatCurrency(forecastValue, '₱0.00')})`;
            forecastEl.classList.toggle('text-red-600', forecastValue < 0);
            forecastEl.classList.toggle('dark:text-red-400', forecastValue < 0);
            forecastEl.classList.toggle('text-blue-600', forecastValue >= 0);
            forecastEl.classList.toggle('dark:text-sky-400', forecastValue >= 0);
        }
        if (invoicedEl) {
            invoicedEl.textContent = formatCurrency(invoicedValue, '₱0.00');
            invoicedEl.classList.toggle('text-red-600', invoicedValue < 0);
            invoicedEl.classList.toggle('dark:text-red-400', invoicedValue < 0);
            invoicedEl.classList.toggle('text-green-600', invoicedValue >= 0);
            invoicedEl.classList.toggle('dark:text-green-400', invoicedValue >= 0);
        }
        if (percentageEl) {
            percentageEl.textContent = percentageText;
        }
        if (monthBlockEl) {
            monthBlockEl.classList.remove('bg-blue-100', 'dark:bg-sky-800', 'border-blue-500', 'dark:border-sky-500', 'ring-2', 'ring-blue-300', 'dark:ring-sky-600');
            monthBlockEl.classList.add('bg-white', 'dark:bg-slate-700', 'border-gray-200', 'dark:border-slate-600');
            if (isCurrentMonth) {
                console.log(`    - Highlighting current month: ${monthAbbr.toUpperCase()}`);
                monthBlockEl.classList.remove('bg-white', 'dark:bg-slate-700', 'border-gray-200', 'dark:border-slate-600');
                monthBlockEl.classList.add('bg-blue-100', 'dark:bg-sky-800', 'border-blue-500', 'dark:border-sky-500', 'ring-2', 'ring-blue-300', 'dark:ring-sky-600');
            }
        }
    });
    console.log("  - Finished updating monthly forecast/invoiced elements and highlighting.");
    console.log("  - Dashboard metrics update complete.");
    console.groupEnd();
}

function populateUpdatesList(updates, listElement) {
    console.groupCollapsed(`UI: Populating Updates List (${updates?.length || 0} items)`);
    if (!listElement) {
        console.warn("    - List element not provided.");
        console.groupEnd();
        return;
    }
    listElement.innerHTML = '';
    if (!updates || updates.length === 0) {
        listElement.innerHTML = '<li class="list-group-item text-sm italic text-gray-500 dark:text-slate-400">No updates recorded.</li>';
        console.log("    - No updates to display.");
        console.groupEnd();
        return;
    }
    const svgCheck = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>`;
    const svgSquare = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 7.5A2.25 2.25 0 0 1 7.5 5.25h9a2.25 2.25 0 0 1 2.25 2.25v9a2.25 2.25 0 0 1-2.25 2.25h-9a2.25 2.25 0 0 1-2.25-2.25v-9Z" /></svg>`;
    const svgTrash = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>`;
    const fragment = document.createDocumentFragment();
    updates.forEach(update => {
        const li = document.createElement('li');
        li.className = `list-group-item update-item ${update.is_completed ? 'update-completed' : ''} flex justify-between items-center py-1 border-b last:border-b-0 border-gray-200 dark:border-slate-700`;
        li.dataset.updateId = update.update_id;
        const completedIcon = update.is_completed ? svgCheck : svgSquare;
        const completedText = update.is_completed ? 'Mark Incomplete' : 'Mark Complete';
        const completionTimestamp = update.completion_timestamp ? `(Done: ${formatDate(update.completion_timestamp)})` : '';
        const dueDateText = update.due_date ? ` (Due: ${formatDate(update.due_date)})` : '';
        const buttonBaseClass = "btn-action p-1 rounded";
        li.innerHTML = `
            <span class="update-text text-sm mr-2 ${update.is_completed ? 'line-through text-gray-400 dark:text-slate-500' : 'text-gray-800 dark:text-slate-300'}">
                ${update.update_text || 'N/A'}
                <small class="text-xs text-gray-500 dark:text-slate-400 ml-1">${dueDateText}${completionTimestamp}</small>
            </span>
            <div class="update-actions flex-shrink-0 ml-auto space-x-1 flex items-center">
                <button class="${buttonBaseClass} toggle-button ${update.is_completed ? 'text-gray-500 hover:text-gray-700 dark:text-slate-500 dark:hover:text-slate-300' : 'text-green-600 hover:text-green-800 dark:text-green-500 dark:hover:text-green-400'}"
                        data-action="toggle-update" data-update-id="${update.update_id}" title="${completedText}">
                    ${completedIcon}
                </button>
                <button class="${buttonBaseClass} delete-button text-red-500 hover:text-red-700 dark:text-red-500 dark:hover:text-red-400"
                        data-action="delete-update" data-update-id="${update.update_id}" title="Delete Update">
                    ${svgTrash}
                </button>
            </div>
        `;
        fragment.appendChild(li);
    });
    listElement.appendChild(fragment);
    console.log("    - Updates list populated.");
    console.groupEnd();
}

function renderProjectTable(dataToRender, tableBody, isCompletedTable = false) {
    const tableName = isCompletedTable ? 'Completed' : 'Active';
    console.groupCollapsed(`UI: Rendering ${tableName} Project Table (${dataToRender?.length || 0} rows)`);
    if (!tableBody) {
        console.warn(`    - Table body element not found for ${tableName} table.`);
        console.groupEnd();
        return;
    }
    tableBody.innerHTML = '';
    if (!dataToRender || dataToRender.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="12" class="text-center p-4 italic text-gray-500 dark:text-slate-400">No ${tableName.toLowerCase()} projects found.</td></tr>`;
        console.log(`    - No ${tableName.toLowerCase()} projects to display.`);
        console.groupEnd();
        return;
    }
    const svgEye = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>`;
    const svgPencil = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" /></svg>`;
    const svgTrash = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>`;
    const svgCurrencyDollar = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33" /></svg>`;
    const svgChartBar = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>`;
    // START: SVG for MRF (Document Text Icon)
    const svgDocumentText = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 inline-block align-middle"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 5.25 6h.008a2.25 2.25 0 0 1 2.242 2.135l.002.006a2.25 2.25 0 0 0-.004.006l-.002.006a2.251 2.251 0 0 1-2.242 2.135H5.25A2.25 2.25 0 0 1 3 10.5V8.25a2.25 2.25 0 0 1 2.25-2.25h5.25ZM7.5 15h3M7.5 18h3M3 15h.008v.008H3V15Zm0 3h.008v.008H3v-.008Z" /></svg>`;
    // END: SVG for MRF
    const fragment = document.createDocumentFragment();
    try {
        dataToRender.forEach((project) => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-sky-50 dark:hover:bg-slate-700/50';
            tr.dataset.projectId = project.id;
            const poDateStr = formatDate(project.po_date);
            const completedDateStr = formatDate(project.date_completed);
            const hasForecasts = project.has_forecasts;
            const forecastIndicator = hasForecasts ? `<span class="forecast-indicator text-xs ml-1" title="Has Forecast Items">📈</span>` : '';
            const buttonBaseClass = "btn-action p-1 rounded focus:outline-none focus:ring-1 focus:ring-offset-1 dark:focus:ring-offset-slate-800";
            const latestUpdatePreview = project.latest_update ? project.latest_update.substring(0, 50) + (project.latest_update.length > 50 ? '...' : '') : '<span class="text-xs italic text-gray-500 dark:text-slate-400">No updates</span>';

            // Construct query parameters for MRF link
            const mrfParams = new URLSearchParams({
                project_id: project.id, // Pass project ID as well
                project_name: project.project_name || '',
                project_number: project.project_no || '', // Use project_no if projectNumber isn't directly available
                client: project.client || ''
            }).toString();
            const mrfLink = `/mrf_form?${mrfParams}`; // Ensure /mrf_form is the correct route

            tr.innerHTML = `
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-24">${project.project_no || ''} ${forecastIndicator}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-48">${project.project_name || 'N/A'}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-32">${project.client || ''}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-28 text-right">${formatCurrency(project.amount)}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-20 text-right editable-cell cursor-pointer hover:bg-blue-100 dark:hover:bg-sky-900" data-field="status" data-project-id="${project.id}">${formatPercent(project.status)}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-28 text-right remaining-amount-cell">${formatCurrency(project.remaining_amount)}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-16 text-center ${project.total_running_weeks > 40 ? 'text-red-600 dark:text-red-400 font-bold' : ''}">${project.total_running_weeks ?? ''}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-24">${poDateStr}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-20 text-center">${project.pic || ''}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-64 updates-column whitespace-normal align-top" title="${project.latest_update || ''}">${latestUpdatePreview}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-24">${completedDateStr}</td>
                <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-sm w-auto action-column space-x-1 flex flex-wrap items-center">
                    <button class="${buttonBaseClass} text-blue-600 hover:text-blue-800 dark:text-sky-500 dark:hover:text-sky-400 focus:ring-blue-300 dark:focus:ring-sky-600" data-action="view-details" data-project-id="${project.id}" title="View Details & Updates">${svgEye}</button>
                    <button class="${buttonBaseClass} text-yellow-600 hover:text-yellow-800 dark:text-amber-500 dark:hover:text-amber-400 focus:ring-yellow-300 dark:focus:ring-amber-600 ${isCompletedTable ? 'hidden' : ''}" data-action="edit" data-project-id="${project.id}" title="Edit Project">${svgPencil}</button>
                    <button class="${buttonBaseClass} text-red-600 hover:text-red-800 dark:text-red-500 dark:hover:text-red-400 focus:ring-red-300 dark:focus:ring-red-600 ${isCompletedTable ? 'hidden' : ''}" data-action="delete" data-project-id="${project.id}" data-project-name="${project.project_name || 'N/A'}" title="Delete Project">${svgTrash}</button>
                    <button class="${buttonBaseClass} text-green-600 hover:text-green-800 dark:text-green-500 dark:hover:text-green-400 focus:ring-green-300 dark:focus:ring-green-600 ${isCompletedTable ? 'hidden' : ''}" data-action="add-forecast" data-project-id="${project.id}" title="Add Forecast Entry">${svgCurrencyDollar}</button>
                    <a href="${mrfLink}" class="${buttonBaseClass} text-purple-600 hover:text-purple-800 dark:text-purple-400 dark:hover:text-purple-300 focus:ring-purple-300 dark:focus:ring-purple-600 inline-flex items-center ${isCompletedTable ? 'hidden' : ''}" title="Create MRF for this Project">${svgDocumentText}</a>
                    <a href="/project_gantt?project_id=${project.id}" class="${buttonBaseClass} text-gray-600 hover:text-gray-800 dark:text-slate-400 dark:hover:text-slate-300 focus:ring-gray-300 dark:focus:ring-slate-600 inline-flex items-center" title="View Gantt Chart" target="_blank">${svgChartBar}</a>
                </td>
            `;
            fragment.appendChild(tr);
        });
    } catch (renderError) {
        console.error(`    - [renderProjectTable - ${tableName}] Error during row creation loop:`, renderError);
        tableBody.innerHTML = `<tr class="error"><td colspan="12">Error rendering project data. Check console for details.</td></tr>`;
        console.groupEnd();
        return;
    }
    tableBody.appendChild(fragment);
    console.log(`    - ${tableName} table rendered.`);
    console.groupEnd();
}

function renderActiveTable() {
    console.groupCollapsed("UI: Sorting & Rendering Active Table");
    let dataToRender = [...currentProjectsData];
    if (currentSort.key) {
        const { key, direction } = currentSort;
        console.log(`    - Sorting by: ${key}, Direction: ${direction}`);
        const sortMultiplier = direction === 'asc' ? 1 : -1;
        const numericKeys = ['amount', 'status', 'remaining_amount', 'total_running_weeks', 'year'];
        const dateKeys = ['po_date', 'date_completed'];
        try {
            dataToRender.sort((a, b) => {
                let valA = a[key], valB = b[key];
                if (key === 'latest_update') {
                    const textA = String(a.latest_update || '').toLowerCase();
                    const textB = String(b.latest_update || '').toLowerCase();
                    if (!textA && textB) return 1;
                    if (textA && !textB) return -1;
                    if (!textA && !textB) return 0;
                    if (textA < textB) return -1 * sortMultiplier;
                    if (textA > textB) return 1 * sortMultiplier;
                    return 0;
                } else if (dateKeys.includes(key)) {
                    const dateA = parseDate(valA);
                    const dateB = parseDate(valB);
                    const timeA = dateA ? dateA.getTime() : (direction === 'asc' ? Infinity : -Infinity);
                    const timeB = dateB ? dateB.getTime() : (direction === 'asc' ? Infinity : -Infinity);
                    return (timeA - timeB) * sortMultiplier;
                } else if (numericKeys.includes(key)) {
                    const numA = safeFloat(valA, direction === 'asc' ? Infinity : -Infinity);
                    const numB = safeFloat(valB, direction === 'asc' ? Infinity : -Infinity);
                    return (numA - numB) * sortMultiplier;
                } else {
                    valA = String(valA ?? '').toLowerCase();
                    valB = String(valB ?? '').toLowerCase();
                    if (!valA && valB) return 1;
                    if (valA && !valB) return -1;
                    if (!valA && !valB) return 0;
                    if (valA < valB) return -1 * sortMultiplier;
                    if (valA > valB) return 1 * sortMultiplier;
                    return 0;
                }
            });
            console.log("    - Sorting complete.");
        } catch (sortError) {
            console.error("    - Error during sorting:", sortError);
        }
    } else {
        console.log("    - No sort key defined, rendering unsorted.");
    }
    renderProjectTable(dataToRender, getElement('activeProjectsTableBody'), false);
    console.groupEnd();
}

function renderCompletedTable() {
    console.groupCollapsed("UI: Sorting & Rendering Completed Table");
    let dataToRender = [...currentCompletedProjectsData];
    if (currentSort.key) {
        const { key, direction } = currentSort;
        console.log(`    - Sorting by: ${key}, Direction: ${direction}`);
        const sortMultiplier = direction === 'asc' ? 1 : -1;
        const numericKeys = ['amount', 'status', 'remaining_amount', 'total_running_weeks', 'year'];
        const dateKeys = ['po_date', 'date_completed'];
        try {
            dataToRender.sort((a, b) => {
                let valA = a[key], valB = b[key];
                if (key === 'latest_update') {
                    const textA = String(a.latest_update || '').toLowerCase();
                    const textB = String(b.latest_update || '').toLowerCase();
                    if (!textA && textB) return 1;
                    if (textA && !textB) return -1;
                    if (!textA && !textB) return 0;
                    if (textA < textB) return -1 * sortMultiplier;
                    if (textA > textB) return 1 * sortMultiplier;
                    return 0;
                } else if (dateKeys.includes(key)) {
                    const dateA = parseDate(valA);
                    const dateB = parseDate(valB);
                    const timeA = dateA ? dateA.getTime() : (direction === 'asc' ? Infinity : -Infinity);
                    const timeB = dateB ? dateB.getTime() : (direction === 'asc' ? Infinity : -Infinity);
                    return (timeA - timeB) * sortMultiplier;
                } else if (numericKeys.includes(key)) {
                    const numA = safeFloat(valA, direction === 'asc' ? Infinity : -Infinity);
                    const numB = safeFloat(valB, direction === 'asc' ? Infinity : -Infinity);
                    return (numA - numB) * sortMultiplier;
                } else {
                    valA = String(valA ?? '').toLowerCase();
                    valB = String(valB ?? '').toLowerCase();
                    if (!valA && valB) return 1;
                    if (valA && !valB) return -1;
                    if (!valA && !valB) return 0;
                    if (valA < valB) return -1 * sortMultiplier;
                    if (valA > valB) return 1 * sortMultiplier;
                    return 0;
                }
            });
            console.log("    - Sorting complete.");
        } catch (sortError) {
            console.error("    - Error during sorting:", sortError);
        }
    } else {
        console.log("    - No sort key defined, rendering unsorted.");
    }
    renderProjectTable(dataToRender, getElement('completedProjectsTableBody'), true);
    console.groupEnd();
}

// --- Filtering & Sorting ---
function applyFiltersAndRender() {
    console.log("Applying filters and rendering active table (currently only sorting).");
    renderActiveTable();
}

// --- Modal Opening Functions ---
function openAddProjectModal() {
    console.groupCollapsed("UI: Open Add Project Modal");
    const addProjectModal = getElement('addProjectModal');
    const addProjectForm = getElement('addProjectForm');
    if (!addProjectModal || !addProjectForm) {
        console.error("    - Add project modal or form elements not found.");
        console.groupEnd();
        return;
    }
    clearFeedback();
    addProjectForm.reset();
    addProjectForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    addProjectModal.classList.remove('hidden');
    addProjectModal.classList.add('flex');
    getElement('add-project_name')?.focus();
    console.log("    - Add Project modal opened.");
    console.groupEnd();
}

function openEditModal(projectId) {
    console.groupCollapsed(`UI: Open Edit Project Modal (ID: ${projectId})`);
    const editProjectModal = getElement('editProjectModal');
    const editProjectForm = getElement('editProjectForm');
    if (!editProjectModal || !editProjectForm) {
        console.error("    - Edit project modal or form elements not found.");
        console.groupEnd();
        return;
    }
    clearFeedback();
    const project = currentProjectsData.find(p => p.id === projectId)
        || currentCompletedProjectsData.find(p => p.id === projectId);
    if (!project) {
        displayFeedback(`Error: Project with ID ${projectId} not found.`, 'error');
        console.error(`    - Project with ID ${projectId} not found in local data.`);
        console.groupEnd();
        return;
    }
    console.log("    - Found project data:", project);
    editProjectForm.reset();
    editProjectForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    editProjectForm.dataset.projectId = project.id;
    getElement('edit-project_name').value = project.project_name || '';
    getElement('edit-project_no').value = project.project_no || '';
    getElement('edit-client').value = project.client || '';
    getElement('edit-amount').value = project.amount ?? '';
    getElement('edit-status').value = project.status ?? '';
    getElement('edit-po_date').value = project.po_date ? project.po_date.split('T')[0] : '';
    getElement('edit-po_no').value = project.po_no || '';
    getElement('edit-date_completed').value = project.date_completed ? project.date_completed.split('T')[0] : '';
    getElement('edit-pic').value = project.pic || '';
    getElement('edit-address').value = project.address || '';
    getElement('edit-ds').value = project.ds || '';
    getElement('edit-year').value = project.year ?? '';
    editProjectModal.classList.remove('hidden');
    editProjectModal.classList.add('flex');
    getElement('edit-project_name')?.focus();
    console.log("    - Edit modal opened and populated.");
    console.groupEnd();
}

async function openProjectDetailsModal(projectId) {
    console.groupCollapsed(`UI: Open Project Details Modal (ID: ${projectId})`);
    const projectModal = getElement('projectModal');
    if (!projectModal) {
        console.error("    - Project details modal element not found.");
        console.groupEnd();
        return;
    }
    clearFeedback();
    const project = currentProjectsData.find(p => p.id === projectId)
        || currentCompletedProjectsData.find(p => p.id === projectId);
    if (!project) {
        displayFeedback(`Error: Project ID ${projectId} not found.`, 'error');
        console.error(`    - Project with ID ${projectId} not found in local data.`);
        console.groupEnd();
        return;
    }
    console.log("    - Found project data:", project);
    getElement('modalProjectName').textContent = project.project_name || 'N/A';
    getElement('modalProjectNo').textContent = project.project_no || 'N/A';
    getElement('modalClient').textContent = project.client || 'N/A';
    getElement('modalAmount').textContent = formatCurrency(project.amount);
    getElement('modalStatus').textContent = formatPercent(project.status);
    getElement('modalRemaining').textContent = formatCurrency(project.remaining_amount);
    getElement('modalPODate').textContent = formatDate(project.po_date);
    getElement('modalPONo').textContent = project.po_no || 'N/A';
    getElement('modalPIC').textContent = project.pic || 'N/A';
    getElement('modalAddress').textContent = project.address || 'N/A';
    getElement('modalDateCompleted').textContent = formatDate(project.date_completed);
    getElement('modalRunningWeeks').textContent = project.total_running_weeks ?? 'N/A';
    getElement('modalDS').textContent = project.ds || 'N/A';
    getElement('modalYear').textContent = project.year || 'N/A';
    console.log("    - Static details populated.");
    const addUpdateForm = getElement('addUpdateForm');
    const addUpdateMessage = getElement('addUpdateMessage');
    if (addUpdateForm) {
        addUpdateForm.dataset.projectId = project.id;
        addUpdateForm.reset();
        if (addUpdateMessage) addUpdateMessage.textContent = '';
        addUpdateForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        console.log("    - Add Update form prepared.");
    }
    projectModal.classList.remove('hidden');
    projectModal.classList.add('flex');
    console.log("    - Details modal displayed.");
    const updates = await fetchProjectUpdates(projectId);
    populateUpdatesList(updates, getElement('projectUpdatesList'));
    console.groupEnd();
}

function openForecastModal(projectId) {
    console.groupCollapsed(`UI: Open Forecast Modal (ID: ${projectId})`);
    const forecastModal = getElement('forecast-modal');
    const forecastForm = getElement('forecast-form');
    const forecastProjectIdInput = getElement('forecast-modal-project-id');
    const forecastProjectInfoSpan = getElement('forecast-project-info');
    const forecastDateInput = getElement('forecast-date');
    const forecastAmountInput = getElement('forecast-amount');
    const forecastPercentInput = getElement('forecast-percent');
    const forecastDeductCheckbox = getElement('forecast-deduct-checkbox');
    const forecastDeductionPercentContainer = getElement('forecast-deduction-percent-container');
    const forecastDeductionPercentInput = getElement('forecast-deduction-percent');
    const forecastErrorMessageEl = getElement('forecast-error-message');
    if (!forecastModal || !forecastForm || !forecastProjectIdInput || !forecastProjectInfoSpan || !forecastDateInput || !forecastAmountInput || !forecastPercentInput || !forecastDeductCheckbox) {
        console.error("    - Cannot open forecast form (missing required HTML elements).");
        displayFeedback("Cannot open forecast form (missing required HTML elements).", "error");
        console.groupEnd();
        return;
    }
    const project = currentProjectsData.find(p => p.id === projectId)
        || currentCompletedProjectsData.find(p => p.id === projectId);
    if (!project) {
        displayFeedback(`Error: Project ID ${projectId} not found.`, 'error');
        console.error(`    - Project with ID ${projectId} not found in local data.`);
        console.groupEnd();
        return;
    }
    console.log("    - Found project data:", project);
    clearFeedback();
    forecastForm.reset();
    if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = '';
    forecastForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    forecastProjectIdInput.value = project.id;
    forecastProjectInfoSpan.textContent = `${project.project_name || 'N/A'} (ID: ${project.id})`;
    try {
        forecastDateInput.value = new Date().toISOString().split('T')[0];
    } catch (e) { console.error("    - Error setting default date:", e) }
    forecastDeductCheckbox.checked = false;
    if (forecastDeductionPercentContainer) forecastDeductionPercentContainer.style.display = 'none';
    if (forecastDeductionPercentInput) forecastDeductionPercentInput.value = '';
    forecastModal.classList.remove('hidden');
    forecastModal.classList.add('flex');
    if (forecastAmountInput) forecastAmountInput.focus();
    console.log("    - Forecast modal opened and prepared.");
    console.groupEnd();
}

function closeForecastModal() {
    console.log("UI: Closing Forecast Modal");
    const forecastModal = getElement('forecast-modal');
    const forecastErrorMessageEl = getElement('forecast-error-message');
    if (forecastModal) {
        forecastModal.classList.add('hidden');
        forecastModal.classList.remove('flex');
        if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = '';
    }
}

// --- Form Submission Handlers ---
async function handleAddProjectSubmit(event) {
    console.groupCollapsed("FORM: Handle Add Project Submit");
    event.preventDefault();
    const addProjectForm = getElement('addProjectForm');
    const addProjectModal = getElement('addProjectModal');
    if (!addProjectForm) {
        console.error("    - Add project form not found.");
        console.groupEnd();
        return;
    }
    clearFeedback();
    const formData = new FormData(addProjectForm);
    const projectData = {};
    let isValid = true;
    const projectName = formData.get('project_name')?.trim();
    if (!projectName) {
        displayFeedback("Project Name is required.", 'error');
        getElement('add-project_name')?.classList.add('is-invalid');
        isValid = false;
        console.warn("    - Validation failed: Project Name required.");
    } else {
        getElement('add-project_name')?.classList.remove('is-invalid');
    }
    if (!isValid) {
        console.groupEnd();
        return;
    }
    formData.forEach((value, key) => {
        projectData[key] = value.trim() === '' ? null : value.trim();
    });
    projectData.amount = safeFloat(projectData.amount, null);
    projectData.status = safeFloat(projectData.status, 0.0);
    projectData.year = safe_int(projectData.year, null);
    console.log("    - Prepared project data:", projectData);
    const submitButton = addProjectForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    displayFeedback("Adding project...", "info");
    try {
        const result = await apiFetch(BULK_PROJECTS_API, { method: 'POST', body: [projectData] });
        displayFeedback(result.message || 'Project added successfully!', 'success');
        if (result.errors?.length) {
            displayFeedback(`Project added. Warnings: ${result.errors.join('; ')}`, 'warning');
            console.warn("    - Backend warnings:", result.errors);
        }
        addProjectForm.reset();
        addProjectModal?.classList.add('hidden');
        addProjectModal?.classList.remove('flex');
        console.log("    - Project added, modal closed.");
        await fetchActiveProjects();
        await fetchDashboardData();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Error adding project:", error);
            displayFeedback(`Error adding project: ${error.data?.error || error.message || 'Unknown error'}`, 'error');
        }
    } finally {
        if (submitButton) submitButton.disabled = false;
        console.groupEnd();
    }
}

async function handleEditSubmit(event) {
    console.groupCollapsed("FORM: Handle Edit Project Submit");
    event.preventDefault();
    const editProjectForm = getElement('editProjectForm');
    const editProjectModal = getElement('editProjectModal');
    if (!editProjectForm) {
        console.error("    - Edit project form not found.");
        console.groupEnd();
        return;
    }
    clearFeedback();
    const projectId = editProjectForm.dataset.projectId;
    if (!projectId) {
        displayFeedback("Error: Project ID missing for edit.", 'error');
        console.error("    - Project ID missing from form dataset.");
        console.groupEnd();
        return;
    }
    console.log(`    - Editing Project ID: ${projectId}`);
    const formData = new FormData(editProjectForm);
    const updatedFields = {};
    let isValid = true;
    const allowedFields = ['client', 'status', 'po_date', 'po_no', 'date_completed', 'pic', 'address', 'amount', 'project_name', 'year', 'ds'];
    allowedFields.forEach(field => {
        if (formData.has(field)) {
            const value = formData.get(field).trim();
            updatedFields[field] = (value === '' && field !== 'project_name') ? null : value;
        }
    });
    console.log("    - Raw updated fields collected:", updatedFields);
    if (updatedFields.project_name === null || updatedFields.project_name === '') { displayFeedback("Project Name cannot be empty.", 'error'); getElement('edit-project_name')?.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Project Name empty."); }
    else { getElement('edit-project_name')?.classList.remove('is-invalid'); }
    if ('amount' in updatedFields) {
        if (updatedFields.amount !== null) {
            const numAmount = safeFloat(updatedFields.amount);
            if (isNaN(numAmount)) { displayFeedback("Invalid Amount.", 'error'); isValid = false; getElement('edit-amount')?.classList.add('is-invalid'); console.warn("    - Validation failed: Invalid Amount."); }
            else { updatedFields.amount = numAmount; getElement('edit-amount')?.classList.remove('is-invalid'); }
        } else { getElement('edit-amount')?.classList.remove('is-invalid'); }
    }
    if ('status' in updatedFields) {
        if (updatedFields.status !== null) {
            const numStatus = safeFloat(updatedFields.status);
            if (isNaN(numStatus) || numStatus < 0 || numStatus > 100) { displayFeedback("Status must be 0-100.", 'error'); isValid = false; getElement('edit-status')?.classList.add('is-invalid'); console.warn("    - Validation failed: Invalid Status."); }
            else { updatedFields.status = numStatus; getElement('edit-status')?.classList.remove('is-invalid'); }
        } else { updatedFields.status = 0.0; getElement('edit-status')?.classList.remove('is-invalid'); }
    }
    if ('year' in updatedFields) {
        if (updatedFields.year !== null) {
            const numYear = safe_int(updatedFields.year);
            if (numYear === null) { displayFeedback("Invalid Year.", 'error'); isValid = false; getElement('edit-year')?.classList.add('is-invalid'); console.warn("    - Validation failed: Invalid Year."); }
            else { updatedFields.year = numYear; getElement('edit-year')?.classList.remove('is-invalid'); }
        } else { getElement('edit-year')?.classList.remove('is-invalid'); }
    }
    if (updatedFields.po_date && !parseDate(updatedFields.po_date)) { displayFeedback("Invalid PO Date format.", 'error'); isValid = false; getElement('edit-po_date')?.classList.add('is-invalid'); console.warn("    - Validation failed: Invalid PO Date."); }
    else { getElement('edit-po_date')?.classList.remove('is-invalid'); }
    if (updatedFields.date_completed && !parseDate(updatedFields.date_completed)) { displayFeedback("Invalid Date Completed format.", 'error'); isValid = false; getElement('edit-date_completed')?.classList.add('is-invalid'); console.warn("    - Validation failed: Invalid Date Completed."); }
    else { getElement('edit-date_completed')?.classList.remove('is-invalid'); }
    if (!isValid) {
        console.groupEnd();
        return;
    }
    if (Object.keys(updatedFields).length === 0) {
        displayFeedback("No changes detected to save.", "info");
        console.log("    - No changes detected.");
        console.groupEnd();
        return;
    }
    console.log("    - Validated fields to send:", updatedFields);
    const submitButton = editProjectForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    displayFeedback("Saving...", "info");
    try {
        const result = await apiFetch(UPDATE_PROJECT_API(projectId), { method: 'PUT', body: updatedFields });
        console.log("    - Update successful, result:", result);
        displayFeedback(result.message || 'Project updated!', 'success');
        editProjectModal?.classList.add('hidden');
        editProjectModal?.classList.remove('flex');
        console.log("    - Edit modal closed.");
        await fetchActiveProjects();
        await fetchCompletedProjects();
        await fetchDashboardData();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Error updating project:", error);
            const errorDetails = error.data?.details ? ` Details: ${error.data.details.join(', ')}` : '';
            displayFeedback(`Error updating: ${error.message}${errorDetails}`, 'error');
        }
    } finally {
        if (submitButton) submitButton.disabled = false;
        console.groupEnd();
    }
}

async function handleAddUpdateSubmit(event) {
    console.groupCollapsed("FORM: Handle Add Update Submit");
    event.preventDefault();
    const addUpdateForm = getElement('addUpdateForm');
    const addUpdateMessage = getElement('addUpdateMessage');
    if (!addUpdateForm) {
        console.error("    - Add update form not found.");
        console.groupEnd();
        return;
    }
    const projectId = addUpdateForm.dataset.projectId;
    const updateText = addUpdateForm.elements['update_text']?.value.trim();
    const dueDate = addUpdateForm.elements['update_due_date']?.value;
    if (!projectId) { displayFeedback("Error: Project ID missing.", 'error'); console.error("    - Project ID missing from form dataset."); console.groupEnd(); return; }
    if (!updateText) {
        displayFeedback("Update text cannot be empty.", 'error');
        addUpdateForm.elements['update_text']?.classList.add('is-invalid');
        console.warn("    - Validation failed: Update text empty.");
        console.groupEnd();
        return;
    } else {
        addUpdateForm.elements['update_text']?.classList.remove('is-invalid');
    }
    let validatedDueDate = null;
    if (dueDate && dueDate.trim() !== '') {
        if (!parseDate(dueDate)) {
            displayFeedback("Invalid Due Date format.", 'error');
            addUpdateForm.elements['update_due_date']?.classList.add('is-invalid');
            console.warn("    - Validation failed: Invalid Due Date.");
            console.groupEnd();
            return;
        } else {
            validatedDueDate = dueDate;
            addUpdateForm.elements['update_due_date']?.classList.remove('is-invalid');
        }
    } else {
        addUpdateForm.elements['update_due_date']?.classList.remove('is-invalid');
    }
    const updateData = { update_text: updateText, due_date: validatedDueDate };
    console.log(`    - Adding update for Project ID ${projectId}:`, updateData);
    const submitButton = addUpdateForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    if (addUpdateMessage) { addUpdateMessage.textContent = 'Adding...'; addUpdateMessage.className = 'message info text-xs mt-1'; }
    try {
        const result = await apiFetch(PROJECT_UPDATES_API(projectId), { method: 'POST', body: updateData });
        if (addUpdateMessage) addUpdateMessage.textContent = '';
        addUpdateForm.reset();
        console.log("    - Update added successfully.");
        const updates = await fetchProjectUpdates(projectId);
        populateUpdatesList(updates, getElement('projectUpdatesList'));
        await fetchActiveProjects();
        await fetchCompletedProjects();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Error adding update:", error);
            const errorMsg = `Error: ${error.data?.error || error.message || 'Unknown error'}`;
            if (addUpdateMessage) { addUpdateMessage.textContent = errorMsg; addUpdateMessage.className = 'message error text-xs mt-1 text-red-600 dark:text-red-400'; }
            displayFeedback(`Error adding update: ${errorMsg}`, 'error');
        }
    } finally {
        if (submitButton) submitButton.disabled = false;
        console.groupEnd();
    }
}

async function handleAddForecastSubmit(event) {
    console.groupCollapsed("FORM: Handle Add Forecast Submit");
    event.preventDefault();
    const forecastForm = getElement('forecast-form');
    const forecastModal = getElement('forecast-modal');
    const forecastProjectIdInput = getElement('forecast-modal-project-id');
    const forecastAmountInput = getElement('forecast-amount');
    const forecastPercentInput = getElement('forecast-percent');
    const forecastDateInput = getElement('forecast-date');
    const forecastDeductCheckbox = getElement('forecast-deduct-checkbox');
    const forecastErrorMessageEl = getElement('forecast-error-message');
    if (!forecastForm || !forecastModal || !forecastProjectIdInput || !forecastAmountInput || !forecastPercentInput || !forecastDateInput || !forecastDeductCheckbox) {
        if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Form elements missing.';
        console.error("    - Forecast form elements missing.");
        console.groupEnd();
        return;
    }
    const projectId = forecastProjectIdInput.value;
    const amountStr = forecastAmountInput.value.trim();
    const percentStr = forecastPercentInput.value.trim();
    const dateValue = forecastDateInput.value;
    const isDeductionChecked = forecastDeductCheckbox.checked;
    if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = '';
    forecastAmountInput.classList.remove('is-invalid');
    forecastPercentInput.classList.remove('is-invalid');
    forecastDateInput.classList.remove('is-invalid');
    let forecast_input_type = '', original_input_value = null, isValid = true;
    let valueFieldProvided = false;
    if (amountStr) {
        const numAmount = safeFloat(amountStr);
        if (isNaN(numAmount)) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Invalid Amount.'; forecastAmountInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Invalid Amount."); }
        else { forecast_input_type = 'amount'; original_input_value = numAmount; valueFieldProvided = true; }
    }
    if (percentStr) {
        if (valueFieldProvided) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Enter Amount OR Percent, not both.'; if (amountStr) forecastAmountInput.classList.add('is-invalid'); forecastPercentInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Both Amount and Percent entered."); }
        else {
            const numPercent = safeFloat(percentStr);
            if (isNaN(numPercent)) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Invalid Percent.'; forecastPercentInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Invalid Percent."); }
            else { forecast_input_type = 'percent'; original_input_value = numPercent; valueFieldProvided = true; }
        }
    }
    if (!projectId || isNaN(parseInt(projectId, 10))) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Project ID missing.'; isValid = false; console.error("    - Validation failed: Project ID missing."); }
    if (!dateValue) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Date required.'; forecastDateInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Date required."); }
    else if (!parseDate(dateValue)) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Invalid Date format.'; forecastDateInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Invalid Date format."); }
    if (!valueFieldProvided && isValid) { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Error: Enter Amount or Percent.'; forecastAmountInput.classList.add('is-invalid'); forecastPercentInput.classList.add('is-invalid'); isValid = false; console.warn("    - Validation failed: Neither Amount nor Percent entered."); }
    if (!isValid) {
        console.groupEnd();
        return;
    }
    let final_value_to_send = original_input_value;
    let final_is_deduction_flag = isDeductionChecked;
    if (isDeductionChecked) {
        final_value_to_send = original_input_value * 0.30;
        console.log(`    - Deduction Calculation (${forecast_input_type}): Original ${original_input_value}, Sending 30%: ${final_value_to_send}`);
    } else {
        console.log(`    - No Deduction: Sending original ${forecast_input_type}: ${final_value_to_send}`);
    }
    const forecastData = {
        project_id: parseInt(projectId, 10),
        forecast_input_type: forecast_input_type,
        forecast_input_value: final_value_to_send,
        forecast_date: dateValue,
        is_deduction: final_is_deduction_flag
    };
    console.log("    - Sending Forecast Data:", forecastData);
    const submitButton = forecastForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = 'Adding...';
    try {
        await apiFetch(ADD_FORECAST_API, { method: 'POST', body: forecastData });
        displayFeedback('Forecast added!', 'success');
        closeForecastModal();
        console.log("    - Forecast added successfully.");
        await fetchDashboardData();
        await fetchActiveProjects();
        await fetchCompletedProjects();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - Error adding forecast:", error);
            const errorMsg = `Error: ${error.data?.error || error.message || 'Unknown error'}`;
            if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = errorMsg;
            displayFeedback(`Error adding forecast: ${errorMsg}`, 'error');
        }
    } finally {
        if (submitButton) submitButton.disabled = false;
        if (forecastErrorMessageEl?.textContent === 'Adding...') {
            forecastErrorMessageEl.textContent = '';
        }
        console.groupEnd();
    }
}

async function handleCsvUpload(event) {
    console.groupCollapsed("FORM: Handle CSV Upload");
    event.preventDefault();
    const csvUploadForm = getElement('csvUploadForm');
    const csvFileInput = getElement('csv-file');
    const csvMessage = getElement('csv-message');
    if (!csvUploadForm || !csvFileInput || !csvMessage) {
        console.error("    - CSV Upload form elements missing.");
        console.groupEnd();
        return;
    }
    if (!csvFileInput.files?.length) {
        csvMessage.textContent = 'Please select a CSV file.';
        csvMessage.className = 'message error text-xs text-red-600 dark:text-red-400';
        console.warn("    - No CSV file selected.");
        console.groupEnd();
        return;
    }
    const file = csvFileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.csv')) {
        csvMessage.textContent = 'Invalid file type. Please select a .csv file.';
        csvMessage.className = 'message error text-xs text-red-600 dark:text-red-400';
        console.warn("    - Invalid file type selected.");
        console.groupEnd();
        return;
    }
    console.log(`    - Selected file: ${file.name}`);
    const formData = new FormData();
    formData.append('csv-file', file);
    csvMessage.textContent = 'Uploading and processing...';
    csvMessage.className = 'message info text-xs text-blue-600 dark:text-sky-400';
    const submitButton = csvUploadForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    try {
        const result = await apiFetch(UPLOAD_CSV_API, { method: 'POST', body: formData });
        console.log("    - CSV Upload API Result:", result);
        let messageText = result.message || 'CSV processed.';
        let messageType = 'success';
        if (result.errors?.length) {
            messageText += ` Warnings/Skipped:\n - ${result.errors.slice(0, 5).join('\n - ')}`;
            if (result.errors.length > 5) messageText += `\n - ...and ${result.errors.length - 5} more.`;
            console.warn("    - CSV Upload Warnings/Skipped:", result.errors);
            messageType = (result.inserted_count > 0 || result.updated_count > 0) ? 'warning' : 'error';
        }
        csvMessage.textContent = messageText;
        const typeClasses = { success: 'text-green-600 dark:text-green-400', error: 'text-red-600 dark:text-red-400', warning: 'text-yellow-600 dark:text-amber-500', info: 'text-blue-600 dark:text-sky-400' };
        csvMessage.className = `message mt-3 text-sm whitespace-pre-line ${typeClasses[messageType] || typeClasses['info']}`;
        console.log(`    - Final CSV message displayed (type: ${messageType}).`);
        if (result.inserted_count > 0 || result.updated_count > 0) {
            console.log("    - Refreshing data due to CSV changes.");
            await fetchActiveProjects();
            await fetchCompletedProjects();
            await fetchDashboardData();
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error("    - CSV Upload failed:", error);
            csvMessage.textContent = `Upload failed: ${error.data?.error || error.message || 'Unknown error'}`;
            csvMessage.className = 'message error text-xs text-red-600 dark:text-red-400';
        }
    } finally {
        if (submitButton) submitButton.disabled = false;
        console.groupEnd();
    }
}

// --- Action Handlers (Triggered by Event Delegation) ---
async function handleTableAction(event) {
    const button = event.target.closest('button[data-action], a[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    const projectId = parseInt(button.dataset.projectId ?? '', 10);
    const updateId = parseInt(button.dataset.updateId ?? '', 10);
    if (button.tagName === 'A' && action && action !== 'view-gantt' && action !== 'create-mrf') { // Allow create-mrf to proceed if it's a link
        event.preventDefault();
    } else if (button.tagName === 'A' && (action === 'view-gantt' || action === 'create-mrf')) {
        console.log(`ACTION: Allowing default navigation for ${action} link (Project ID: ${projectId})`);
        // For create-mrf, the link itself will handle navigation with params
        if (action === 'create-mrf') return; // Do not prevent default for MRF link
    }
    console.groupCollapsed(`ACTION: ${action} (ProjectID: ${projectId || 'N/A'}, UpdateID: ${updateId || 'N/A'})`);
    try {
        switch (action) {
            case 'view-details':
                if (!isNaN(projectId)) openProjectDetailsModal(projectId);
                else console.error("    - Missing projectId for view-details");
                break;
            case 'edit':
                if (!isNaN(projectId)) openEditModal(projectId);
                else console.error("    - Missing projectId for edit");
                break;
            case 'delete':
                if (!isNaN(projectId)) {
                    const name = button.dataset.projectName || `ID ${projectId}`;
                    deleteProject(projectId, name);
                } else console.error("    - Missing projectId for delete");
                break;
            case 'add-forecast':
                if (!isNaN(projectId)) openForecastModal(projectId);
                else console.error("    - Missing projectId for add-forecast");
                break;
            case 'toggle-update':
                if (!isNaN(updateId)) toggleUpdateCompletion(updateId);
                else console.error("    - Missing updateId for toggle-update");
                break;
            case 'delete-update':
                if (!isNaN(updateId)) deleteUpdate(updateId);
                else console.error("    - Missing updateId for delete-update");
                break;
            // case 'create-mrf': // This is now handled by direct link navigation
            //     if (!isNaN(projectId)) {
            //         const project = currentProjectsData.find(p => p.id === projectId) || currentCompletedProjectsData.find(p => p.id === projectId);
            //         if (project) {
            //             const params = new URLSearchParams({
            //                 project_id: project.id,
            //                 project_name: project.project_name || '',
            //                 project_number: project.project_no || '',
            //                 client: project.client || ''
            //             });
            //             window.location.href = `/mrf_form?${params.toString()}`;
            //         } else {
            //             console.error("    - Project not found for create-mrf");
            //         }
            //     } else console.error("    - Missing projectId for create-mrf");
            //     break;
            default:
                console.log(`    - Unhandled or irrelevant action: ${action}`);
                break;
        }
    } catch (e) {
        console.error(`    - Error during action handling (${action}):`, e);
    } finally {
        console.groupEnd();
    }
}

async function deleteProject(projectId, projectName) {
    console.groupCollapsed(`ACTION: Delete Project (ID: ${projectId}, Name: "${projectName}")`);
    const confirmationMessage = `DELETE Project "${projectName}" (ID: ${projectId})?\n\nThis action permanently deletes the project and ALL its associated updates, tasks, and forecast entries.\n\nTHIS CANNOT BE UNDONE.`;
    if (!confirm(confirmationMessage)) {
        console.log("    - Deletion cancelled by user.");
        console.groupEnd();
        return;
    }
    displayFeedback(`Deleting project ${projectId}...`, 'info');
    try {
        await apiFetch(UPDATE_PROJECT_API(projectId), { method: 'DELETE' });
        displayFeedback(`Project ${projectId} ("${projectName}") deleted successfully.`, 'success');
        console.log("    - Project deleted successfully.");
        await fetchActiveProjects();
        await fetchCompletedProjects();
        await fetchDashboardData();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error(`    - Error deleting project ${projectId}:`, error);
            displayFeedback(`Error deleting project ${projectId}: ${error.message}`, 'error');
        }
    } finally {
        console.groupEnd();
    }
}

async function toggleUpdateCompletion(updateId) {
    console.groupCollapsed(`ACTION: Toggle Update Completion (ID: ${updateId})`);
    const listItem = document.querySelector(`li[data-update-id="${updateId}"]`);
    const button = listItem?.querySelector('button[data-action="toggle-update"]');
    if (button) button.disabled = true;
    try {
        const result = await apiFetch(UPDATE_TOGGLE_API(updateId), { method: 'PUT' });
        console.log("    - Toggle API result:", result);
        if (listItem && result) {
            const textSpan = listItem.querySelector('.update-text');
            const smallText = listItem.querySelector('small');
            const isCompleted = result.is_completed;
            listItem.classList.toggle('update-completed', isCompleted);
            if (textSpan) {
                textSpan.classList.toggle('line-through', isCompleted);
                textSpan.classList.toggle('text-gray-400', isCompleted);
                textSpan.classList.toggle('dark:text-slate-500', isCompleted);
                textSpan.classList.toggle('text-gray-800', !isCompleted);
                textSpan.classList.toggle('dark:text-slate-300', !isCompleted);
            }
            if (smallText) {
                const dueDateText = result.due_date ? ` (Due: ${formatDate(result.due_date)})` : '';
                const completionTimestamp = isCompleted && result.completion_timestamp ? ` (Done: ${formatDate(result.completion_timestamp)})` : '';
                smallText.textContent = `${dueDateText}${completionTimestamp}`;
            }
            if (button) {
                button.title = isCompleted ? 'Mark Incomplete' : 'Mark Complete';
                const svgCheck = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>`;
                const svgSquare = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 7.5A2.25 2.25 0 0 1 7.5 5.25h9a2.25 2.25 0 0 1 2.25 2.25v9a2.25 2.25 0 0 1-2.25 2.25h-9a2.25 2.25 0 0 1-2.25-2.25v-9Z" /></svg>`;
                button.innerHTML = isCompleted ? svgCheck : svgSquare;
                button.classList.toggle('text-gray-500', isCompleted);
                button.classList.toggle('hover:text-gray-700', isCompleted);
                button.classList.toggle('dark:text-slate-500', isCompleted);
                button.classList.toggle('dark:hover:text-slate-300', isCompleted);
                button.classList.toggle('text-green-600', !isCompleted);
                button.classList.toggle('hover:text-green-800', !isCompleted);
                button.classList.toggle('dark:text-green-500', !isCompleted);
                button.classList.toggle('dark:hover:text-green-400', !isCompleted);
            }
            console.log(`    - Update ${updateId} UI toggled to completed: ${isCompleted}`);
        } else {
            console.warn("    - List item or result missing, cannot update UI.");
        }
        await fetchActiveProjects();
        await fetchCompletedProjects();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error(`    - Error toggling update ${updateId}:`, error);
            displayFeedback(`Error toggling update: ${error.message}`, 'error');
        }
    } finally {
        if (button) button.disabled = false;
        console.groupEnd();
    }
}

async function deleteUpdate(updateId) {
    console.groupCollapsed(`ACTION: Delete Update (ID: ${updateId})`);
    if (!confirm('Are you sure you want to delete this update permanently?')) {
        console.log("    - Deletion cancelled by user.");
        console.groupEnd();
        return;
    }
    const listItem = document.querySelector(`li[data-update-id="${updateId}"]`);
    const button = listItem?.querySelector('button[data-action="delete-update"]');
    if (button) button.disabled = true;
    try {
        await apiFetch(UPDATE_SINGLE_API(updateId), { method: 'DELETE' });
        listItem?.remove();
        displayFeedback('Update deleted.', 'success');
        console.log("    - Update deleted successfully.");
        await fetchActiveProjects();
        await fetchCompletedProjects();
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error(`    - Error deleting update ${updateId}:`, error);
            displayFeedback(`Error deleting update: ${error.message}`, 'error');
            if (button) button.disabled = false;
        }
    } finally {
        console.groupEnd();
    }
}

// --- Inline Editing Functions ---
function makeCellEditable(cell) {
    console.groupCollapsed(`UI: Make Cell Editable`);
    console.log("    - Cell clicked:", cell);
    if (currentlyEditingCell && currentlyEditingCell !== cell) {
        displayFeedback("Please save or cancel the other edit first.", "warning");
        console.warn("    - Another cell is already being edited.");
        console.groupEnd();
        return;
    }
    if (currentlyEditingCell === cell) {
        console.log("    - Cell is already in edit mode.");
        console.groupEnd();
        return;
    }
    const fieldKey = cell.dataset.field;
    const projectId = cell.dataset.projectId;
    console.log(`    - Field: ${fieldKey}, Project ID: ${projectId}`);
    if (fieldKey !== 'status') {
        console.warn("    - Inline editing not supported for field:", fieldKey);
        console.groupEnd();
        return;
    }
    currentlyEditingCell = cell;
    const originalDisplayValue = cell.textContent.trim();
    let originalNumericValue = originalDisplayValue;
    let inputValue = originalDisplayValue;
    let inputType = 'text';
    let inputClasses = 'inline-edit-input form-input p-0 border-blue-300 dark:border-sky-700 focus:ring-1 focus:ring-blue-500 dark:focus:ring-sky-500 h-full bg-white dark:bg-slate-800';
    if (fieldKey === 'status') {
        inputType = 'number';
        inputValue = safeFloat(originalDisplayValue, 0);
        originalNumericValue = inputValue;
        inputClasses += ' text-right';
    }
    console.log(`    - Original Value: "${originalDisplayValue}", Input Value: ${inputValue}`);
    cell.dataset.originalValue = originalDisplayValue;
    cell.innerHTML = '';
    cell.classList.remove('cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
    const input = document.createElement('input');
    input.type = inputType;
    input.value = inputValue;
    input.className = inputClasses;
    if (inputType === 'number') {
        input.step = '0.1';
        input.min = '0';
        input.max = '100';
    }
    input.style.height = 'calc(100% - 2px)';
    input.style.width = 'calc(100% - 2px)';
    cell.appendChild(input);
    input.focus();
    input.select();
    console.log("    - Input element created and focused.");
    const handleBlur = () => {
        setTimeout(() => {
            if (document.activeElement !== input && cell === currentlyEditingCell) {
                console.log("    - Input blurred, attempting save...");
                saveEdit(input, cell, projectId, fieldKey, originalNumericValue);
            }
        }, 150);
    };
    const handleKeyDown = (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            console.log("    - Enter key pressed, attempting save...");
            saveEdit(input, cell, projectId, fieldKey, originalNumericValue);
        } else if (event.key === 'Escape') {
            console.log("    - Escape key pressed, cancelling edit...");
            cancelEdit(input, cell, originalDisplayValue);
        }
    };
    input.addEventListener('blur', handleBlur);
    input.addEventListener('keydown', handleKeyDown);
    cell._inlineEditListeners = { blur: handleBlur, keydown: handleKeyDown };
    console.groupEnd();
}

async function saveEdit(inputElement, cell, projectId, fieldKey, originalValue) {
    console.groupCollapsed(`ACTION: Save Inline Edit (Project ID: ${projectId}, Field: ${fieldKey})`);
    if (!cell || cell !== currentlyEditingCell) {
        console.warn("    - Save aborted: Cell is no longer the active editing cell.");
        console.groupEnd();
        return;
    }
    const listeners = cell._inlineEditListeners;
    if (listeners) {
        inputElement.removeEventListener('blur', listeners.blur);
        inputElement.removeEventListener('keydown', listeners.keydown);
        delete cell._inlineEditListeners;
    }
    currentlyEditingCell = null;
    console.log("    - Listeners removed, edit lock released.");
    const newValue = inputElement.value.trim();
    let valueToSend = newValue;
    let displayValue = newValue;
    let changed = false;
    if (fieldKey === 'status') {
        const numericValue = safeFloat(newValue);
        if (isNaN(numericValue) || numericValue < 0 || numericValue > 100) {
            displayFeedback('Invalid Status value. Must be between 0 and 100.', 'error');
            cell.textContent = formatPercent(originalValue);
            cell.classList.add('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
            console.warn("    - Validation failed: Invalid Status value. Reverted display.");
            console.groupEnd();
            return;
        }
        valueToSend = numericValue;
        displayValue = formatPercent(numericValue);
        changed = parseFloat(valueToSend.toFixed(1)) !== parseFloat(originalValue.toFixed(1));
    } else {
        console.error("    - Trying to save unhandled editable field:", fieldKey);
        cell.textContent = cell.dataset.originalValue || '';
        cell.classList.add('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
        console.groupEnd();
        return;
    }
    console.log(`    - New Value: "${newValue}", Value to Send: ${valueToSend}, Changed: ${changed}`);
    if (!changed) {
        cell.textContent = displayValue;
        cell.classList.add('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
        console.log("    - No change detected, reverted display.");
        console.groupEnd();
        return;
    }
    cell.textContent = 'Saving...';
    cell.classList.remove('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
    try {
        const result = await apiFetch(UPDATE_PROJECT_API(projectId), {
            method: 'PUT',
            body: { [fieldKey]: valueToSend }
        });
        console.log("    - API Update Result:", result);
        cell.textContent = displayValue;
        const projectIndexActive = currentProjectsData.findIndex(p => p.id == projectId);
        const projectIndexCompleted = currentCompletedProjectsData.findIndex(p => p.id == projectId);
        const updatedProjectData = result.updatedProject;
        if (updatedProjectData) {
            console.log("    - Updating local cache with data:", updatedProjectData);
            if (projectIndexActive > -1) {
                currentProjectsData[projectIndexActive] = { ...currentProjectsData[projectIndexActive], ...updatedProjectData };
            } else if (projectIndexCompleted > -1) {
                currentCompletedProjectsData[projectIndexCompleted] = { ...currentCompletedProjectsData[projectIndexCompleted], ...updatedProjectData };
            } else {
                console.warn("    - Project ID", projectId, "not found in local cache after update. Re-fetching lists.");
                fetchActiveProjects(); fetchCompletedProjects();
            }
            if (fieldKey === 'status' || fieldKey === 'amount') {
                const row = cell.closest('tr');
                const remainingCell = row?.querySelector('.remaining-amount-cell');
                if (remainingCell) remainingCell.textContent = formatCurrency(updatedProjectData.remaining_amount);
                console.log("    - Status/Amount changed, refreshing dashboard.");
                fetchDashboardData();
            }
            console.log("    - Local cache and related cells updated.");
        } else {
            console.warn("    - Backend did not return updated project data. Re-fetching lists.");
            fetchActiveProjects(); fetchCompletedProjects();
            if (fieldKey === 'status' || fieldKey === 'amount') fetchDashboardData();
        }
    } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error(`    - Error updating ${fieldKey}:`, error);
            displayFeedback(`Error updating ${fieldKey}: ${error.message}`, 'error');
            cell.textContent = (fieldKey === 'status') ? formatPercent(originalValue) : (cell.dataset.originalValue || '');
        }
    } finally {
        cell.classList.add('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
        console.groupEnd();
    }
}

function cancelEdit(inputElement, cell, originalDisplayValue) {
    console.groupCollapsed(`ACTION: Cancel Inline Edit`);
    if (!cell || cell !== currentlyEditingCell) {
        console.warn("    - Cancel aborted: Cell is not the active editing cell.");
        console.groupEnd();
        return;
    }
    const listeners = cell._inlineEditListeners;
    if (listeners) {
        inputElement.removeEventListener('blur', listeners.blur);
        inputElement.removeEventListener('keydown', listeners.keydown);
        delete cell._inlineEditListeners;
    }
    cell.textContent = originalDisplayValue;
    cell.classList.add('editable-cell', 'cursor-pointer', 'hover:bg-blue-100', 'dark:hover:bg-sky-900');
    delete cell.dataset.originalValue;
    currentlyEditingCell = null;
    console.log("    - Edit cancelled, original value restored.");
    console.groupEnd();
}

// --- CSV Handling ---
function exportToCSV(dataToExport, filenamePrefix) {
    console.groupCollapsed(`UTIL: Export to CSV (${filenamePrefix})`);
    if (!dataToExport || dataToExport.length === 0) {
        displayFeedback(`No data available to export for ${filenamePrefix}.`, 'warning');
        console.warn("    - No data to export.");
        console.groupEnd();
        return;
    }
    console.log(`    - Exporting ${dataToExport.length} rows.`);
    const headers = ["DS", "Year", "Project #", "Client", "Project Name", "Amount", "Status (%)", "Remaining", "Weeks", "PO Date", "PO No.", "Date Completed", "PIC", "Latest Update", "Address"];
    const csvHeaderString = headers.map(formatCsvCell).join(',');
    const csvRows = [csvHeaderString];
    try {
        dataToExport.forEach(project => {
            const latestUpdateText = project.latest_update ?? '';
            const poDateExport = formatDate(project.po_date, '');
            const completedDateExport = formatDate(project.date_completed, '');
            const row = [
                project.ds ?? '', project.year ?? '', project.project_no ?? '', project.client ?? '',
                project.project_name ?? '', safeFloat(project.amount, ''), safeFloat(project.status, ''),
                safeFloat(project.remaining_amount, ''), project.total_running_weeks ?? '', poDateExport,
                project.po_no ?? '', completedDateExport, project.pic ?? '', latestUpdateText, project.address ?? ''
            ];
            csvRows.push(row.map(formatCsvCell).join(','));
        });
        const csvString = csvRows.join('\n');
        const blob = new Blob([`\uFEFF${csvString}`], { type: 'text/csv;charset=utf-8;' });
        const now = new Date();
        const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
        const filename = `${filenamePrefix}_Export_${timestamp}.csv`;
        console.log(`    - Generated filename: ${filename}`);
        const link = document.createElement('a');
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.href = url;
            link.download = filename;
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            console.log("    - Download triggered via link.");
        } else if (navigator.msSaveBlob) {
            navigator.msSaveBlob(blob, filename);
            console.log("    - Download triggered via msSaveBlob.");
        } else {
            displayFeedback("CSV export is not fully supported by your browser.", "error");
            console.error("    - Browser does not support CSV download methods.");
        }
    } catch (error) {
        console.error(`    - [exportToCSV - ${filenamePrefix}] Error:`, error);
        displayFeedback("An error occurred while exporting data to CSV.", "error");
    } finally {
        console.groupEnd();
    }
}

function exportActiveToCSV() {
    exportToCSV(currentProjectsData, 'Active_Projects');
}

function exportCompletedToCSV() {
    exportToCSV(currentCompletedProjectsData, 'Completed_Projects');
}

// --- UI Control Functions ---
function toggleNavigation() {
    console.groupCollapsed("UI: Toggle Navigation");
    const sideNav = getElement('side-nav');
    sideNav?.classList.toggle('nav-collapsed');
    try {
        const isCollapsed = sideNav?.classList.contains('nav-collapsed');
        localStorage.setItem('navCollapsed', isCollapsed ? 'true' : 'false');
        console.log(`    - Nav state toggled. Collapsed: ${isCollapsed}. Saved to localStorage.`);
    } catch (e) {
        console.warn("    - Could not save nav state to localStorage:", e);
    }
    console.groupEnd();
}

function toggleSettingsSubmenu() {
    console.log("UI: Toggle Settings Submenu");
    const settingsSubMenu = getElement('settings-submenu');
    settingsSubMenu?.classList.toggle('hidden');
}

function toggleTheme() {
    console.groupCollapsed("UI: Toggle Theme");
    const isDark = document.documentElement.classList.toggle('dark');
    try {
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        console.log(`    - Theme toggled. Is Dark: ${isDark}. Saved to localStorage.`);
    } catch (e) {
        console.warn("    - Could not save theme state to localStorage:", e);
    }
    console.groupEnd();
}

function applyInitialNavState(sideNavElement) {
    console.groupCollapsed("UI: Apply Initial Nav State");
    try {
        if (localStorage.getItem('navCollapsed') === 'true') {
            sideNavElement?.classList.add('nav-collapsed');
            console.log("    - Applying collapsed state from localStorage.");
        } else {
            sideNavElement?.classList.remove('nav-collapsed');
            console.log("    - Applying expanded state from localStorage (or default).");
        }
    } catch (e) {
        console.warn("    - Could not read nav state from localStorage:", e);
    }
    console.groupEnd();
}

function applyInitialTheme() {
    console.groupCollapsed("UI: Apply Initial Theme");
    try {
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
            document.documentElement.classList.add('dark');
            console.log(`    - Applying dark theme (Saved: ${savedTheme}, Prefers: ${prefersDark}).`);
        } else {
            document.documentElement.classList.remove('dark');
            console.log(`    - Applying light theme (Saved: ${savedTheme}, Prefers: ${prefersDark}).`);
        }
    } catch (e) {
        console.warn("    - Could not read theme state from localStorage:", e);
    }
    console.groupEnd();
}

function setupCollapsibleSections() {
    console.groupCollapsed("UI: Setup Collapsible Sections Listener");
    document.body.addEventListener('click', (event) => {
        const toggleBtn = event.target.closest('.toggle-section-btn');
        if (toggleBtn) {
            console.groupCollapsed("UI: Collapsible Toggle Clicked");
            console.log("    - Button:", toggleBtn);
            const targetId = toggleBtn.getAttribute('data-target');
            if (!targetId) {
                console.warn("    - Collapsible toggle button missing data-target attribute:", toggleBtn);
                console.groupEnd();
                return;
            }
            const targetContent = getElement(targetId);
            const parentSection = toggleBtn.closest('.collapsible');
            console.log(`    - Target ID: ${targetId}, Content Found: ${!!targetContent}, Parent Found: ${!!parentSection}`);
            if (targetContent && parentSection) {
                const isCurrentlyCollapsed = parentSection.classList.contains('collapsed');
                console.log(`    - Currently Collapsed: ${isCurrentlyCollapsed}`);
                targetContent.classList.toggle('hidden', isCurrentlyCollapsed);
                parentSection.classList.toggle('collapsed', !isCurrentlyCollapsed);
                toggleBtn.setAttribute('aria-expanded', !isCurrentlyCollapsed ? 'true' : 'false');
                const iconContainer = toggleBtn.querySelector('.toggle-icon');
                if (iconContainer) {
                    iconContainer.style.transform = !isCurrentlyCollapsed ? 'rotate(0deg)' : 'rotate(-90deg)';
                }
                console.log(`    - New State - Collapsed: ${!isCurrentlyCollapsed}`);
                if (targetId === 'completed-projects-content' && !isCurrentlyCollapsed && currentCompletedProjectsData.length === 0) {
                    console.log("    - Fetching completed projects on expand...");
                    fetchCompletedProjects();
                }
            } else {
                if (!targetContent) console.warn(`    - Collapsible content with ID '${targetId}' not found.`);
                if (!parentSection) console.warn("    - Could not find parent '.collapsible' element for toggle button:", toggleBtn);
            }
            console.groupEnd();
        }
    });
    console.log("    - Collapsible section listener setup on body.");
    console.groupEnd();
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.groupCollapsed("🚀 App Initialization Sequence");
    const initStartTime = performance.now();
    console.log(`DOM loaded at ${new Date().toLocaleTimeString()}. Initializing app...`);
    console.groupCollapsed("DOM Element References");
    const sideNav = getElement('side-nav');
    const navToggleBtn = getElement('nav-main-toggle-btn');
    const settingsToggleBtn = getElement('settings-toggle-btn');
    const settingsSubMenu = getElement('settings-submenu');
    const dashboardLoadingEl = getElement('dashboardLoading');
    const dashboardErrorEl = getElement('dashboardError');
    const activeProjectsTableBody = getElement('activeProjectsTableBody');
    const completedProjectsTableBody = getElement('completedProjectsTableBody');
    const activeProjectsLoadingEl = getElement('activeProjectsLoading');
    const activeProjectsErrorEl = getElement('activeProjectsError');
    const completedProjectsLoadingEl = getElement('completedProjectsLoading');
    const completedProjectsErrorEl = getElement('completedProjectsError');
    const addProjectBtn = getElement('addProjectBtn');
    const openCsvModalBtn = getElement('open-csv-modal-btn');
    const exportActiveCsvBtn = getElement('export-active-csv-btn');
    const exportCompletedCsvBtn = getElement('export-completed-csv-btn');
    const addProjectModal = getElement('addProjectModal');
    const addProjectForm = getElement('addProjectForm');
    const editProjectModal = getElement('editProjectModal');
    const editProjectForm = getElement('editProjectForm');
    const projectModal = getElement('projectModal');
    const projectUpdatesList = getElement('projectUpdatesList');
    const updatesLoading = getElement('updatesLoading');
    const updatesError = getElement('updatesError');
    const addUpdateForm = getElement('addUpdateForm');
    const addUpdateMessage = getElement('addUpdateMessage');
    const csvUploadModal = getElement('csv-upload-modal');
    const csvUploadForm = getElement('csvUploadForm');
    const csvFileInput = getElement('csv-file');
    const csvMessage = getElement('csv-message');
    const forecastModal = getElement('forecast-modal');
    const forecastForm = getElement('forecast-form');
    const forecastCancelBtn = getElement('forecast-cancel-btn');
    const forecastErrorMessageEl = getElement('forecast-error-message');
    const themeToggleBtn = getElement('theme-toggle-btn');
    const userDisplayNameEl = getElement('user-display-name');
    const logoutBtn = getElement('logout-btn');
    const modalsContainer = getElement('modals-container');
    const completedSection = getElement('completedProjectsSection');
    console.log("    - DOM element references obtained.");
    console.groupEnd();
    try {
        applyInitialNavState(sideNav);
        applyInitialTheme();
    } catch (e) {
        console.error("Error applying initial UI states:", e);
    }
    function initializeEventListeners() {
        console.groupCollapsed("🔧 Initializing Event Listeners");
        const startTime = performance.now();
        addProjectForm?.addEventListener('submit', handleAddProjectSubmit);
        editProjectForm?.addEventListener('submit', handleEditSubmit);
        addUpdateForm?.addEventListener('submit', handleAddUpdateSubmit);
        forecastForm?.addEventListener('submit', handleAddForecastSubmit);
        csvUploadForm?.addEventListener('submit', handleCsvUpload);
        console.log("    - Form submit listeners added.");
        addProjectBtn?.addEventListener('click', openAddProjectModal);
        openCsvModalBtn?.addEventListener('click', () => {
            console.log("UI: Open CSV Modal button clicked.");
            if (csvUploadModal) {
                csvUploadModal.classList.remove('hidden');
                csvUploadModal.classList.add('flex');
                if (csvMessage) csvMessage.textContent = '';
                csvUploadForm?.reset();
            }
        });
        exportActiveCsvBtn?.addEventListener('click', exportActiveToCSV);
        exportCompletedCsvBtn?.addEventListener('click', exportCompletedToCSV);
        forecastCancelBtn?.addEventListener('click', closeForecastModal);
        logoutBtn?.addEventListener('click', handleLogout);
        console.log("    - Button click listeners added.");
        themeToggleBtn?.addEventListener('click', toggleTheme);
        navToggleBtn?.addEventListener('click', toggleNavigation);
        settingsToggleBtn?.addEventListener('click', toggleSettingsSubmenu);
        console.log("    - Global UI toggle listeners added.");
        modalsContainer?.addEventListener('click', (event) => {
            const target = event.target;
            const modal = target.closest('.modal');
            if (!modal) return;
            const isCloseButton = target.closest('.close-modal-btn');
            const isBackdropClick = target === modal && !modal.querySelector('.modal-content')?.contains(target);
            if (isCloseButton || isBackdropClick) {
                console.groupCollapsed(`UI: Closing Modal via ${isCloseButton ? 'Button' : 'Backdrop'}`);
                console.log(`    - Closing modal: ${modal.id}`);
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                if (modal.id === 'editProjectModal' && currentlyEditingCell) {
                    console.log("    - Cancelling active inline edit on modal close.");
                    const cell = currentlyEditingCell;
                    const input = cell.querySelector('input');
                    if (input) {
                        const originalDisplayValue = cell.dataset.originalValue || '';
                        cancelEdit(input, cell, originalDisplayValue);
                    }
                }
                if (modal.id === 'csv-upload-modal') { if (csvMessage) csvMessage.textContent = ''; csvUploadForm?.reset(); console.log("    - Resetting CSV upload modal."); }
                if (modal.id === 'forecast-modal') { if (forecastErrorMessageEl) forecastErrorMessageEl.textContent = ''; console.log("    - Clearing forecast error message."); }
                console.groupEnd();
            }
        });
        console.log("    - Delegated modal close listener added.");
        activeProjectsTableBody?.addEventListener('click', handleTableAction);
        completedProjectsTableBody?.addEventListener('click', handleTableAction);
        projectUpdatesList?.addEventListener('click', handleTableAction);
        console.log("    - Delegated table/list action listeners added.");
        activeProjectsTableBody?.addEventListener('dblclick', (event) => {
            const cell = event.target.closest('.editable-cell');
            if (cell) {
                makeCellEditable(cell);
            }
        });
        console.log("    - Delegated inline edit listener added.");
        setupSortListeners();
        console.log("    - Sort listeners setup complete.");
        const forecastDeductCheckbox = getElement('forecast-deduct-checkbox');
        const forecastDeductionPercentContainer = getElement('forecast-deduction-percent-container');
        const forecastDeductionPercentInput = getElement('forecast-deduction-percent');
        forecastDeductCheckbox?.addEventListener('change', () => {
            console.log(`UI: Forecast deduction checkbox changed. Checked: ${forecastDeductCheckbox.checked}`);
            if (forecastDeductionPercentContainer) {
                forecastDeductionPercentContainer.style.display = forecastDeductCheckbox.checked ? 'block' : 'none';
                if (!forecastDeductCheckbox.checked && forecastDeductionPercentInput) {
                    forecastDeductionPercentInput.value = '';
                }
            }
        });
        console.log("    - Forecast deduction checkbox listener added.");
        const duration = performance.now() - startTime;
        console.log(`Event listeners initialized in ${duration.toFixed(1)}ms.`);
        console.groupEnd();
    }
    function setupSortListeners() {
        console.groupCollapsed("UI: Setup Sort Listeners");
        const addSortListenerToTable = (tableId) => {
            const table = getElement(tableId);
            const thead = table?.querySelector('thead');
            if (!thead) {
                console.warn(`    - Thead not found for table ID: ${tableId}`);
                return;
            }
            thead.addEventListener('click', (event) => {
                const header = event.target.closest('.sortable-header');
                if (!header) return;
                const sortKey = header.dataset.sortKey;
                if (!sortKey) return;
                console.groupCollapsed(`UI: Sort Header Clicked (${tableId})`);
                console.log(`    - Header: ${header.textContent.trim()}, Sort Key: ${sortKey}`);
                let nextDirection;
                if (currentSort.key === sortKey) {
                    nextDirection = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    nextDirection = 'asc';
                }
                console.log(`    - Previous Sort: ${currentSort.key} (${currentSort.direction})`);
                console.log(`    - Next Sort: ${sortKey} (${nextDirection})`);
                currentSort = { key: sortKey, direction: nextDirection };
                thead.querySelectorAll('.sortable-header').forEach(th => {
                    const iconSpan = th.querySelector('.sort-icon');
                    if (th === header) {
                        th.setAttribute('aria-sort', nextDirection + 'ending');
                        if (iconSpan) iconSpan.textContent = nextDirection === 'asc' ? ' ▲' : ' ▼';
                    } else {
                        th.removeAttribute('aria-sort');
                        if (iconSpan) iconSpan.textContent = '';
                    }
                });
                console.log("    - Header visuals updated.");
                if (tableId === 'active-project-table') {
                    renderActiveTable();
                } else if (tableId === 'completed-project-table') {
                    renderCompletedTable();
                }
                console.groupEnd();
            });
            console.log(`    - Sort listener added to table: ${tableId}`);
        };
        addSortListenerToTable('active-project-table');
        addSortListenerToTable('completed-project-table');
        console.groupEnd();
    }
    try {
        initializeEventListeners();
        setupCollapsibleSections();
        console.groupCollapsed("📊 Fetching Initial Data");
        const fetchDataStartTime = performance.now();
        fetchUserInfo();
        fetchDashboardData();
        fetchActiveProjects();
        if (completedSection && !completedSection.classList.contains('collapsed')) {
            console.log("    - Initial load: Completed section is visible, fetching data...");
            fetchCompletedProjects();
        } else {
            console.log("    - Initial load: Completed section is collapsed or not found, deferring fetch.");
        }
        const fetchDataDuration = performance.now() - fetchDataStartTime;
        console.log(`Initial data fetch sequence initiated (took ${fetchDataDuration.toFixed(1)}ms to start all fetches).`);
        console.groupEnd();
    } catch (error) {
        console.error("Critical error during initialization sequence:", error);
        displayFeedback("Initialization failed. Please refresh the page.", "error");
    } finally {
        const initDuration = performance.now() - initStartTime;
        console.log(`🚀 App Initialization Sequence finished in ${initDuration.toFixed(1)}ms.`);
        console.groupEnd();
    }
});
console.log("script.js execution finished (script parsed).");
