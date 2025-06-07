// File input handling
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const dropZone = document.getElementById('dropZone');
const errorAlert = document.getElementById('errorAlert');

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
document.getElementById('uploadForm').onsubmit = async (e) => {
    e.preventDefault();
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const preview = document.getElementById('preview');

    if (!fileInput.files.length) return;

    // Reset UI
    loading.style.display = 'block';
    results.innerHTML = '';
    preview.style.display = 'none';
    errorAlert.style.display = 'none';

    try {
        // Convert file to base64
        const file = fileInput.files[0];
        const reader = new FileReader();
        
        const base64Promise = new Promise((resolve, reject) => {
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
        });
        
        reader.readAsDataURL(file);
        const base64Image = await base64Promise;

        // Send base64 image to server
        const response = await fetch('/upload_base64', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image: base64Image
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to process image');
        }
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }

        // Display warning if present
        if (data.warning) {
            showError(data.warning);
        }

        // Display results in a table
        let resultsHtml = '<h2>Processing Results</h2>';
        resultsHtml += '<div class="table-responsive"><table class="table table-striped results-table">';
        resultsHtml += '<thead><tr><th>Question</th><th>Answer</th><th>Fill Ratios</th></tr></thead><tbody>';
        
        // Sort the results by question number
        const sortedResults = Object.entries(data.results).sort((a, b) => {
            const numA = parseInt(a[0].replace('question_', ''));
            const numB = parseInt(b[0].replace('question_', ''));
            return numA - numB;
        });
        
        for (const [question, details] of sortedResults) {
            const questionNum = parseInt(question.replace('question_', ''));
            const answer = details.answer ? details.answer.join(', ') : 'No Answer';
            const fillRatios = details.fill_ratios.map(r => r.toFixed(2)).join(', ');
            
            resultsHtml += `<tr>
                <td>${questionNum}</td>
                <td>${answer}</td>
                <td>${fillRatios}</td>
            </tr>`;
        }
        
        resultsHtml += '</tbody></table></div>';
        results.innerHTML = resultsHtml;
        
        // Display combined image with timestamp to prevent caching
        if (data.combined_image) {
            // Clear any existing image
            preview.src = '';
            // Force browser to reload the image
            preview.src = data.combined_image;
            preview.style.display = 'block';
        }
    } catch (error) {
        showError(error.message);
    } finally {
        loading.style.display = 'none';
    }
};

function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
} 