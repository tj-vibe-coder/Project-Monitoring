// mrf_items_log.js - Frontend logic for mrf_items_log.html

// --- Constants (Specific to this page) ---
// API_BASE_URL is expected to be defined globally by script.js
const MRF_ITEMS_LOG_API = `${API_BASE_URL}/mrf/items/log`;
const MRF_ITEM_UPDATE_API = (itemId) => `${API_BASE_URL}/mrf/item/${itemId}`; // For PUT (update) and DELETE

// --- Global State ---
let allMrfItems = []; // To store all fetched items for client-side filtering
let currentFilters = {
    formNo: '',
    projectName: '',
    status: ''
};

// --- Utility Functions ---
// These utility functions (getElement, displayFeedback, formatDate, apiFetch)
// are assumed to be globally available from script.js.
// If they are not, they would need to be defined here or imported if using modules.

// --- DOM Manipulation & Rendering ---
function renderMrfItemsTable(itemsToRender) {
    // Assumes getElement and formatDate are globally available from script.js
    const tableBody = getElement('mrfItemsLogTableBody');
    const loadingMessage = getElement('loadingMessage');
    const noItemsMessage = getElement('noItemsMessage');

    if (!tableBody || !loadingMessage || !noItemsMessage) {
        console.error("mrf_items_log.js: Table body, loading, or no items message element not found.");
        return;
    }

    tableBody.innerHTML = ''; // Clear existing rows

    if (itemsToRender.length === 0) {
        noItemsMessage.style.display = 'block';
        loadingMessage.style.display = 'none';
        return;
    }

    noItemsMessage.style.display = 'none';
    loadingMessage.style.display = 'none';

    const fragment = document.createDocumentFragment();
    itemsToRender.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
        tr.dataset.itemId = item.id;

        const mrfNo = item.form_no || 'N/A';
        const projectName = item.project_name || 'N/A';
        const mrfDate = formatDate(item.mrf_date);
        const itemNo = item.item_no || '-';
        const partNo = item.part_no || '-';
        const brand = item.brand_name || '-';
        const description = item.description || 'No description';
        const qty = typeof item.qty === 'number' ? item.qty : '-';
        const uom = item.uom || '-';
        const targetInstall = formatDate(item.install_date);
        const currentStatus = item.status || 'Processing';
        let actualDeliveryValue = '';
        if (item.actual_delivery_date) {
            try {
                // Ensure date is parsed correctly, assuming YYYY-MM-DD from server or null
                const dateObj = new Date(item.actual_delivery_date + 'T00:00:00Z'); // Treat as UTC to avoid timezone shifts
                if (!isNaN(dateObj.getTime())) {
                    actualDeliveryValue = dateObj.toISOString().split('T')[0];
                }
            } catch (e) {
                console.warn("mrf_items_log.js: Could not parse actual_delivery_date for input:", item.actual_delivery_date, e);
            }
        }
        const remarks = item.remarks || '-';

        tr.innerHTML = `
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${mrfNo}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${projectName}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${mrfDate}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${itemNo}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${partNo}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${brand}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${description}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs text-right">${qty}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${uom}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${targetInstall}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">
                <select class="status-select" data-item-id="${item.id}">
                    <option value="Processing" ${currentStatus === 'Processing' ? 'selected' : ''}>Processing</option>
                    <option value="Pending Approval" ${currentStatus === 'Pending Approval' ? 'selected' : ''}>Pending Approval</option>
                    <option value="For Purchase Order" ${currentStatus === 'For Purchase Order' ? 'selected' : ''}>For Purchase Order</option>
                    <option value="Awaiting Delivery" ${currentStatus === 'Awaiting Delivery' ? 'selected' : ''}>Awaiting Delivery</option>
                    <option value="Delivered to CMR" ${currentStatus === 'Delivered to CMR' ? 'selected' : ''}>Delivered to CMR</option>
                    <option value="Delivered to Site" ${currentStatus === 'Delivered to Site' ? 'selected' : ''}>Delivered to Site</option>
                    <option value="Cancelled" ${currentStatus === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                    <option value="On Hold" ${currentStatus === 'On Hold' ? 'selected' : ''}>On Hold</option>
                </select>
            </td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">
                <input type="date" class="date-input" value="${actualDeliveryValue}" data-item-id="${item.id}">
            </td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">${remarks}</td>
            <td class="px-2 py-1 border-b border-gray-200 dark:border-slate-700 text-xs">
                <button class="action-button save-button" data-item-id="${item.id}" onclick="handleSaveItemChange(this)">Save</button>
                <button class="action-button delete-button" data-item-id="${item.id}" onclick="handleDeleteItem(this)">Delete</button>
            </td>
        `;
        fragment.appendChild(tr);
    });
    tableBody.appendChild(fragment);
}

// --- API Calls & Data Handling ---
async function fetchMrfItems() {
    // Assumes getElement and apiFetch are globally available
    const loadingMessage = getElement('loadingMessage');
    const noItemsMessage = getElement('noItemsMessage');
    loadingMessage.style.display = 'block';
    noItemsMessage.style.display = 'none';
    getElement('mrfItemsLogTableBody').innerHTML = '';

    try {
        allMrfItems = await apiFetch(MRF_ITEMS_LOG_API);
        applyFiltersAndRender();
    } catch (error) {
        loadingMessage.style.display = 'none';
        noItemsMessage.textContent = 'Failed to load MRF items. Please try again.';
        noItemsMessage.style.display = 'block';
        console.error("mrf_items_log.js: Failed to fetch MRF items:", error);
    }
}

async function handleSaveItemChange(buttonElement) {
    // Assumes getElement, displayFeedback, and apiFetch are globally available
    const itemId = buttonElement.dataset.itemId;
    const row = buttonElement.closest('tr');
    if (!row) return;

    const statusSelect = row.querySelector('.status-select');
    const dateInput = row.querySelector('.date-input');

    const newStatus = statusSelect ? statusSelect.value : null;
    const newDeliveryDate = dateInput ? (dateInput.value || null) : null; // Send null if date is cleared

    // Check if any actual change was made
    const originalItem = allMrfItems.find(i => i.id === parseInt(itemId));
    let originalDeliveryDateFormatted = '';
    if (originalItem && originalItem.actual_delivery_date) {
         try {
            const dateObj = new Date(originalItem.actual_delivery_date + 'T00:00:00Z');
            if (!isNaN(dateObj.getTime())) {
                originalDeliveryDateFormatted = dateObj.toISOString().split('T')[0];
            }
        } catch(e) { /* ignore parsing error for comparison */ }
    }

    if (originalItem && originalItem.status === newStatus && originalDeliveryDateFormatted === (newDeliveryDate || '')) {
        displayFeedback('No changes detected for this item.', 'info');
        return;
    }

    const payload = {};
    if (newStatus !== null) payload.status = newStatus;
    // Send actual_delivery_date only if it's explicitly set or cleared (becomes null)
    // This ensures that if the date field was initially empty and remains empty, we don't send `actual_delivery_date: null` unless it was changed to empty.
    if (dateInput && (dateInput.value !== originalDeliveryDateFormatted) ) {
         payload.actual_delivery_date = newDeliveryDate;
    }


    if (Object.keys(payload).length === 0) {
        displayFeedback('No effective changes to save.', 'info');
        return;
    }

    displayFeedback('Saving changes...', 'info');
    buttonElement.disabled = true;
    const otherButton = row.querySelector(buttonElement.classList.contains('save-button') ? '.delete-button' : '.save-button');
    if (otherButton) otherButton.disabled = true;

    try {
        const result = await apiFetch(MRF_ITEM_UPDATE_API(itemId), {
            method: 'PUT',
            body: payload
        });
        displayFeedback(result.message || 'Item updated successfully!', 'success');
        if (result.item) {
            const index = allMrfItems.findIndex(i => i.id === parseInt(itemId));
            if (index !== -1) {
                allMrfItems[index] = { ...allMrfItems[index], ...result.item };
                // Update the specific row in the table directly
                const cells = row.cells;
                if (result.item.status && cells[10] && cells[10].querySelector('select')) {
                    cells[10].querySelector('select').value = result.item.status;
                }
                if (result.item.hasOwnProperty('actual_delivery_date') && cells[11] && cells[11].querySelector('input')) {
                    let updatedDateValue = '';
                    if (result.item.actual_delivery_date) {
                        try {
                            const dateObj = new Date(result.item.actual_delivery_date + 'T00:00:00Z');
                            if (!isNaN(dateObj.getTime())) {
                                updatedDateValue = dateObj.toISOString().split('T')[0];
                            }
                        } catch (e) { console.warn("mrf_items_log.js: Could not parse updated actual_delivery_date for input:", result.item.actual_delivery_date, e); }
                    }
                    cells[11].querySelector('input').value = updatedDateValue;
                }
            }
        }
    } catch (error) {
        console.error(`mrf_items_log.js: Error updating item ${itemId}:`, error);
        // displayFeedback is handled by apiFetch if it's the shared one
    } finally {
        buttonElement.disabled = false;
        if (otherButton) otherButton.disabled = false;
    }
}

async function handleDeleteItem(buttonElement) {
    // Assumes displayFeedback and apiFetch are globally available
    const itemId = buttonElement.dataset.itemId;
    if (!confirm(`Are you sure you want to delete MRF Item ID ${itemId}? This action cannot be undone.`)) {
        return;
    }

    displayFeedback('Deleting item...', 'info');
    buttonElement.disabled = true;
    const otherButton = buttonElement.closest('tr')?.querySelector(buttonElement.classList.contains('delete-button') ? '.save-button' : '.delete-button');
    if (otherButton) otherButton.disabled = true;

    try {
        const result = await apiFetch(MRF_ITEM_UPDATE_API(itemId), {
            method: 'DELETE'
        });
        displayFeedback(result.message || 'Item deleted successfully!', 'success');
        allMrfItems = allMrfItems.filter(item => item.id !== parseInt(itemId));
        applyFiltersAndRender();
    } catch (error) {
        console.error(`mrf_items_log.js: Error deleting item ${itemId}:`, error);
        const rowStillExists = document.querySelector(`tr[data-item-id="${itemId}"]`);
        if (rowStillExists) { // Re-enable buttons only if deletion failed and row is still there
            buttonElement.disabled = false;
            if (otherButton) otherButton.disabled = false;
        }
    }
}

// --- Filtering Logic ---
function applyFilters() {
    // Assumes getElement is globally available
    currentFilters.formNo = getElement('filterFormNo').value.toLowerCase();
    currentFilters.projectName = getElement('filterProjectName').value.toLowerCase();
    currentFilters.status = getElement('filterStatus').value;
    applyFiltersAndRender();
}

function resetFilters() {
    // Assumes getElement is globally available
    getElement('filterFormNo').value = '';
    getElement('filterProjectName').value = '';
    getElement('filterStatus').value = '';
    currentFilters = { formNo: '', projectName: '', status: '' };
    applyFiltersAndRender();
}

function applyFiltersAndRender() {
    let filteredItems = allMrfItems;

    if (currentFilters.formNo) {
        filteredItems = filteredItems.filter(item => item.form_no && item.form_no.toLowerCase().includes(currentFilters.formNo));
    }
    if (currentFilters.projectName) {
        filteredItems = filteredItems.filter(item => item.project_name && item.project_name.toLowerCase().includes(currentFilters.projectName));
    }
    if (currentFilters.status) {
        filteredItems = filteredItems.filter(item => item.status === currentFilters.status);
    }

    renderMrfItemsTable(filteredItems);
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("MRF Items Log page script (mrf_items_log.js) loaded and DOM ready.");

    // Check if shared functions from script.js are available
    if (typeof getElement !== 'function' ||
        typeof displayFeedback !== 'function' ||
        typeof formatDate !== 'function' ||
        typeof apiFetch !== 'function' ||
        typeof API_BASE_URL === 'undefined') { // Check for API_BASE_URL too
        console.warn("mrf_items_log.js: One or more shared utilities (API_BASE_URL, getElement, displayFeedback, formatDate, apiFetch) are not defined. Ensure script.js is loaded first and defines these globally.");
        // Fallback basic displayFeedback if not found from script.js
        if (typeof displayFeedback !== 'function') {
            window.displayFeedback = function(message, type = 'info') {
                const feedbackDiv = document.getElementById('feedbackMessage');
                if (feedbackDiv) {
                    feedbackDiv.textContent = `${type.toUpperCase()}: ${message}`;
                    feedbackDiv.className = `feedback-message feedback-${type}`;
                    feedbackDiv.style.display = 'block';
                     setTimeout(() => { feedbackDiv.style.display = 'none';}, 5000);
                } else {
                    alert(`${type.toUpperCase()}: ${message}`);
                }
            };
        }
         // Provide a fallback for API_BASE_URL if not defined, though this is not ideal
        if (typeof API_BASE_URL === 'undefined') {
            console.error("mrf_items_log.js: API_BASE_URL is not defined. API calls will likely fail. Defaulting to '/api'.");
            window.API_BASE_URL = '/api'; // Fallback
        }
    }

    // Sidebar and theme initialization (assuming script.js handles this primarily)
    const navToggleBtn = getElement('nav-main-toggle-btn');
    const sideNav = getElement('side-nav');
    if (navToggleBtn && sideNav) {
        navToggleBtn.addEventListener('click', () => {
            sideNav.classList.toggle('nav-collapsed');
            localStorage.setItem('navCollapsed', sideNav.classList.contains('nav-collapsed'));
            if (typeof applyInitialNavState === "function") {
                applyInitialNavState();
            } else {
                const mainContent = getElement('main-content');
                if (mainContent) {
                    mainContent.style.marginLeft = sideNav.classList.contains('nav-collapsed') ? '4rem' : '15rem';
                }
            }
        });
    }

    if (typeof applyInitialNavState === "function") {
        applyInitialNavState();
    } else if (sideNav) { // Basic fallback if shared function isn't there
        const mainContent = getElement('main-content');
        if (localStorage.getItem('navCollapsed') === 'true') {
            sideNav.classList.add('nav-collapsed');
            if (mainContent) mainContent.style.marginLeft = '4rem';
        } else {
            if (mainContent) mainContent.style.marginLeft = '15rem';
        }
    }

    const themeToggleBtnSidebar = getElement('theme-toggle-btn-sidebar');
    if (themeToggleBtnSidebar) {
        themeToggleBtnSidebar.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            const lightIcon = getElement('theme-icon-light-sidebar');
            const darkIcon = getElement('theme-icon-dark-sidebar');
            if (lightIcon && darkIcon) {
                lightIcon.style.display = isDark ? 'none' : 'block';
                darkIcon.style.display = isDark ? 'block' : 'none';
            }
        });
        // Set initial theme icon
        const lightIcon = getElement('theme-icon-light-sidebar');
        const darkIcon = getElement('theme-icon-dark-sidebar');
        if (lightIcon && darkIcon) {
            const isDark = document.documentElement.classList.contains('dark');
            lightIcon.style.display = isDark ? 'none' : 'block';
            darkIcon.style.display = isDark ? 'block' : 'none';
        }
    }
    
    const logoutBtnSidebar = getElement('logout-btn-sidebar');
    if (logoutBtnSidebar && typeof handleLogout === 'function') {
        logoutBtnSidebar.addEventListener('click', handleLogout);
    } else if (logoutBtnSidebar) {
        logoutBtnSidebar.addEventListener('click', () => {
            console.warn("mrf_items_log.js: handleLogout function not found from script.js.");
            alert("Logout function not available.");
        });
    }
    
    if (typeof fetchUserInfo === 'function') {
        fetchUserInfo(); // Assumes fetchUserInfo from script.js will populate user details
    } else {
        console.warn("mrf_items_log.js: fetchUserInfo function not found from script.js. User details in sidebar may not populate.");
        const usernameSidebar = getElement('username-display-sidebar');
        const userRoleSidebar = getElement('user-role-display-sidebar');
        if (usernameSidebar) usernameSidebar.textContent = 'User';
        if (userRoleSidebar) userRoleSidebar.textContent = 'Role';
    }

    fetchMrfItems();
});

// Make functions globally accessible if using inline onclick attributes in HTML
window.applyFilters = applyFilters;
window.resetFilters = resetFilters;
window.handleSaveItemChange = handleSaveItemChange;
window.handleDeleteItem = handleDeleteItem;

console.log("mrf_items_log.js: Script parsed. Event listeners will attach on DOMContentLoaded.");
