// mrf_form.js - Handles MRF Form data display

document.addEventListener('DOMContentLoaded', function() {
    const addMaterialBtn = document.getElementById('add-material-btn');

    let currentMrfData = {}; // To store fetched MRF data

    function populateHeaderFields(headerData) {
        document.getElementById('request-date').value = headerData.requestDate ? headerData.requestDate.split('T')[0] : '';
        document.getElementById('requested-by').value = headerData.requestedBy || '';
        document.getElementById('department').value = headerData.department || '';
        document.getElementById('mrf-status').value = headerData.status || 'Draft';
        // If you have a specific field for formNo to be displayed/editable:
        // const formNoEl = document.getElementById('formNoInputId'); // Replace with actual ID
        // if (formNoEl) formNoEl.value = headerData.formNo || '';
    }

    function formatCurrency(value) {
        const num = parseFloat(value);
        if (isNaN(num)) return '0.00';
        return num.toFixed(2);
    }

    function renderMrfItems(items) {
        const container = document.getElementById('material-details-container');
        if (!container) {
            console.error('#material-details-container not found');
            return;
        }
        container.innerHTML = ''; // Clear previous items

        if (!items || items.length === 0) {
            container.innerHTML = '<p class="text-slate-500 dark:text-slate-400 py-4">No materials added yet.</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'w-full text-sm text-left text-gray-500 dark:text-gray-400 mt-2 table-auto';
        
        const thead = document.createElement('thead');
        thead.className = 'text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400';
        thead.innerHTML = `
            <tr>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">Item No</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">Part No</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">Description</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-right">Qty</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">Unit</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-right">Unit Price</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-right">Total Price</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">Remarks</th>
                <th scope="col" class="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider no-print">Actions</th>
            </tr>
        `;
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        tbody.className = 'bg-white divide-y divide-gray-200 dark:bg-slate-800 dark:divide-gray-700';
        items.forEach(item => {
            const row = tbody.insertRow();
            row.className = 'hover:bg-gray-50 dark:hover:bg-slate-700';
            row.innerHTML = `
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">${item.itemNo || ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">${item.partNo || ''}</td>
                <td class="px-3 py-2 whitespace-normal text-sm text-gray-900 dark:text-gray-200" style="min-width: 150px;">${item.itemDescription || ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200 text-right">${item.quantity || 0}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">${item.unit || ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200 text-right">${formatCurrency(item.unitPrice)}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200 text-right">${formatCurrency(item.totalPrice)}</td>
                <td class="px-3 py-2 whitespace-normal text-sm text-gray-900 dark:text-gray-200" style="min-width: 100px;">${item.remarks || ''}</td>
                <td class="px-3 py-2 whitespace-nowrap text-sm font-medium no-print">
                    <button class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-200" onclick="editMrfItem(${item.id})">Edit</button>
                    <button class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-200 ml-2" onclick="deleteMrfItem(${item.id})">Delete</button>
                </td>
            `;
        });
        table.appendChild(tbody);
        container.appendChild(table);
    }

    function updateSummaryFields() {
        let totalQuantity = 0;
        let totalCost = 0;

        if (currentMrfData.items && currentMrfData.items.length > 0) {
            currentMrfData.items.forEach(item => {
                totalQuantity += parseFloat(item.quantity || 0);
                totalCost += parseFloat(item.totalPrice || 0);
            });
        }
        
        document.getElementById('total-quantity').value = totalQuantity;
        document.getElementById('total-cost').value = formatCurrency(totalCost);
    }

    function clearFormForError() {
        populateHeaderFields({}); // Clear header fields
        const container = document.getElementById('material-details-container');
        if (container) container.innerHTML = '<p class="text-red-500 dark:text-red-400 py-4">Error loading MRF data. Please try again or check the console.</p>';
        currentMrfData = { header: {}, items: [] }; // Reset data
        updateSummaryFields(); // Reset summary to 0
    }

    window.editMrfItem = function(itemId) {
        console.log('Edit item clicked:', itemId);
        alert('Edit functionality not yet implemented.');
        // Future: Implement inline editing or modal form for item
    }

    window.deleteMrfItem = function(itemId) {
        console.log('Delete item clicked:', itemId);
        alert('Delete functionality not yet implemented.');
        // Future: Implement item deletion (confirm, update UI, call backend)
    }

    // Main data loading logic
    const urlParams = new URLSearchParams(window.location.search);
    const mrfIdFromUrl = urlParams.get('mrf_id');
    const mrfFormNoFromUrl = urlParams.get('form_no');
    let loadIdentifier = mrfIdFromUrl || mrfFormNoFromUrl;

    if (loadIdentifier) {
        loadMrfDataFromServer(loadIdentifier)
            .then(data => {
                currentMrfData = data; // Store fetched data
                if (data.header && data.header.id) {
                    const mrfIdInput = document.getElementById('mrf-id');
                    if (mrfIdInput) mrfIdInput.value = data.header.id; // Still useful if other features need mrf-id
                }
                if (data.header) {
                    populateHeaderFields(data.header);
                }
                renderMrfItems(data.items || []); // Ensure items is an array
                updateSummaryFields();
            })
            .catch(err => {
                console.error('Failed to load MRF data:', err);
                alert('Failed to load MRF data: ' + err.message);
                clearFormForError();
            });
    } else {
        // New form, initialize with empty/default state
        currentMrfData = { header: {}, items: [] };
        populateHeaderFields({}); // Clear/default header fields
        renderMrfItems([]); // Show "No materials" message
        updateSummaryFields(); // Set totals to 0
    }

    if (addMaterialBtn) {
        addMaterialBtn.addEventListener('click', function() {
            console.log('Add Material button clicked');
            alert('Add Material functionality not fully implemented yet. This would typically add a new editable row to the items table.');
            // To implement:
            // 1. Ensure currentMrfData.items exists (it should).
            // 2. Create a new blank item object (e.g., with a temporary unique ID).
            // 3. Push to currentMrfData.items.
            // 4. Call renderMrfItems(currentMrfData.items) to re-render the table.
            // 5. The new row in renderMrfItems should be editable inputs.
        });
    }

    async function loadMrfDataFromServer(mrfIdOrFormNo) {
        let url;
        if (/^\d+$/.test(mrfIdOrFormNo)) { // Check if it's a numeric ID
            url = `/api/mrf/${mrfIdOrFormNo}`;
        } else { // Assume it's a form number (string)
            url = `/api/mrf/by_form_no/${encodeURIComponent(mrfIdOrFormNo)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            const errorData = await response.text(); // Try to get more error info
            console.error('Server response:', errorData);
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
        }
        return await response.json();
    }
});
