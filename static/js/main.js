document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const orderRows = document.querySelectorAll('.order-row');

    function filterOrders() {
        const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const selectedStatus = statusFilter ? statusFilter.value : 'all';

        orderRows.forEach(function (row) {
            const text = row.innerText.toLowerCase();
            const rowStatus = row.getAttribute('data-status');
            const matchesSearch = text.includes(query);
            const matchesStatus = selectedStatus === 'all' || rowStatus === selectedStatus;

            if (matchesSearch && matchesStatus) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterOrders);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterOrders);
    }

    const statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach(function (select) {
        applyStatusStyle(select);
        select.addEventListener('change', function () {
            const orderId = this.getAttribute('data-order-id');
            const newStatus = this.value;
            const row = this.closest('.order-row');

            fetch('/api/order/' + orderId + '/status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                if (data.success) {
                    row.setAttribute('data-status', newStatus);
                    applyStatusStyle(select);
                    setTimeout(function () {
                        window.location.reload();
                    }, 250);
                }
            });
        });
    });

    function applyStatusStyle(selectElement) {
        selectElement.classList.remove('status-ready', 'status-work');
        if (selectElement.value === 'Готов к выдаче') {
            selectElement.classList.add('status-ready');
        } else if (selectElement.value === 'В работе' || selectElement.value === 'Диагностика') {
            selectElement.classList.add('status-work');
        }
    }

    const modeExisting = document.getElementById('modeExisting');
    const modeNew = document.getElementById('modeNew');
    const existingClientBlock = document.getElementById('existingClientBlock');
    const newClientBlock = document.getElementById('newClientBlock');

    if (modeExisting && modeNew) {
        modeExisting.addEventListener('change', function () {
            existingClientBlock.classList.remove('d-none');
            newClientBlock.classList.add('d-none');
        });

        modeNew.addEventListener('change', function () {
            existingClientBlock.classList.add('d-none');
            newClientBlock.classList.remove('d-none');
        });
    }

    const servicePreset = document.getElementById('servicePreset');
    const totalCostInput = document.getElementById('totalCostInput');

    if (servicePreset && totalCostInput) {
        servicePreset.addEventListener('change', function () {
            const price = parseFloat(this.value);
            if (price > 0) {
                totalCostInput.value = price;
            }
        });
    }
});
