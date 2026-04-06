document.getElementById('analyzer-form').addEventListener('submit', async function(e) {
    e.preventDefault(); 

    const form = e.target;
    const submitBtn = document.getElementById('submit-btn');
    const loadingDiv = document.getElementById('loading');
    const resultsSection = document.getElementById('results-section');
    const coverLetterOutput = document.getElementById('cover-letter-output');

    resultsSection.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    submitBtn.disabled = true;

    const formData = new FormData(form);

    try {
        // Send data to the Flask backend
        const response = await fetch('/api/generate', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Server error: ${response.status}`);
        }

        // Display the generated cover letter
        coverLetterOutput.value = data.cover_letter || "No cover letter generated.";

        loadingDiv.classList.add('hidden');
        resultsSection.classList.remove('hidden');

    } catch (error) {
        console.error("Error during generation:", error);
        alert("An error occurred: " + error.message);
        loadingDiv.classList.add('hidden');
    } finally {
        submitBtn.disabled = false;
    }
});

document.getElementById('copy-btn').addEventListener('click', () => {
    const coverLetter = document.getElementById('cover-letter-output');
    coverLetter.select();
    document.execCommand('copy');
    
    const copyBtn = document.getElementById('copy-btn');
    const originalText = copyBtn.innerText;
    copyBtn.innerText = "Copied!";
    setTimeout(() => {
        copyBtn.innerText = originalText;
    }, 2000);
});

// Download as PDF functionality
document.getElementById('download-btn').addEventListener('click', async () => {
    const coverLetterText = document.getElementById('cover-letter-output').value;
    const studentName = document.getElementById('student-name').value || "Student";
    const downloadBtn = document.getElementById('download-btn');
    
    if (!coverLetterText || coverLetterText === "No cover letter generated.") {
        alert("Please generate a cover letter first!");
        return;
    }

    // Visual feedback during download
    const originalText = downloadBtn.innerText;
    downloadBtn.innerText = "Generating PDF...";
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/api/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                text: coverLetterText, 
                student_name: studentName 
            })
        });

        if (!response.ok) {
            throw new Error("Failed to generate PDF");
        }

        // Convert the response into a downloadable file (Blob)
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // Create a temporary hidden link to trigger the download
        const a = document.createElement('a');
        a.href = url;
        a.download = `Cover_Letter_${studentName.replace(/\s+/g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        a.remove();
        
    } catch (error) {
        console.error("Error downloading PDF:", error);
        alert("Could not download the PDF. Check the console for details.");
    } finally {
        // Reset button
        downloadBtn.innerText = originalText;
        downloadBtn.disabled = false;
    }
});