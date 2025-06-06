// File input handling
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const dropZone = document.getElementById('dropZone');
const errorAlert = document.getElementById('errorAlert');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const preview = document.getElementById('preview');
const uploadForm = document.getElementById('uploadForm');

// File input change handler
fileInput.addEventListener('change', function(e) {
    if (this.files.length > 0) {
        selectedFile.textContent = `Selected file: ${this.files[0].name}`;
    } else {
        selectedFile.textContent = '';
    }
});

// Drag and drop handling
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropZone.classList.add('dragover');
}

function unhighlight(e) {
    dropZone.classList.remove('dragover');
}

dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    fileInput.files = files;
    if (files.length > 0) {
        selectedFile.textContent = `Selected file: ${files[0].name}`;
    }
}

// Form submission
uploadForm.onsubmit = async (e) => {
    e.preventDefault();
    
    if (!fileInput.files.length) {
        showError('Please select a file first');
        return;
    }

    // Disable form while processing
    setFormState(false);
    
    // Reset UI
    resetUI();

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to upload file');
        }

        const data = await response.json();
        
        if (data.job_id) {
            // Start polling for status
            await pollStatus(data.job_id);
        } else {
            throw new Error('No job ID received');
        }
    } catch (error) {
        showError(error.message);
        setFormState(true);
    }
};

async function pollStatus(jobId) {
    try {
        const response = await fetch(`/status/${jobId}`);
        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const status = await response.json();
        
        switch (status.status) {
            case 'processing':
                // Continue polling
                setTimeout(() => pollStatus(jobId), 1000);
                break;
                
            case 'completed':
                if (status.error) {
                    showError(status.error);
                } else {
                    await displayResults(status.result);
                }
                setFormState(true);
                break;
                
            case 'error':
                showError(status.error || 'Processing failed');
                setFormState(true);
                break;
        }
    } catch (error) {
        showError(error.message);
        setFormState(true);
    }
}

async function displayResults(data) {
    // Display results
    let resultsHtml = '<h2>Processing Results</h2>';
    resultsHtml += '<div class="table-responsive"><table class="table table-striped results-table">';
    resultsHtml += '<thead><tr><th>Question</th><th>Answer</th><th>Fill Ratios</th></tr></thead><tbody>';

    for (const [question, details] of Object.entries(data)) {
        const questionNum = parseInt(question.replace('question_', ''));
        const answer = details.answer ? details.answer.join(', ') : 'No Answer';
        const fillRatios = details.fill_ratios ? details.fill_ratios.map(r => r.toFixed(2)).join(', ') : 'N/A';

        resultsHtml += `<tr>
            <td>${questionNum}</td>
            <td>${answer}</td>
            <td>${fillRatios}</td>
        </tr>`;
    }

    resultsHtml += '</tbody></table></div>';
    results.innerHTML = resultsHtml;

    // Display combined image if available
    if (data.question_1 && data.question_1.image) {
        await loadImage(data.question_1.image);
    }
}

function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            preview.src = src + '?t=' + new Date().getTime();
            preview.style.display = 'block';
            resolve();
        };
        img.onerror = () => {
            showError('Failed to load processed image');
            reject();
        };
        img.src = src;
    });
}

function setFormState(enabled) {
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => button.disabled = !enabled);
    loading.style.display = enabled ? 'none' : 'block';
}

function resetUI() {
    loading.style.display = 'block';
    results.innerHTML = '';
    preview.style.display = 'none';
    errorAlert.style.display = 'none';
}

function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
    loading.style.display = 'none';
} 