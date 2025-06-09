document.addEventListener('DOMContentLoaded', () => {
    // Get references to HTML elements
    const imageUpload = document.getElementById('imageUpload');
    const fileNameDisplay = document.getElementById('fileName');
    const storyContainer = document.getElementById('storyContainer');
    const uploadedImage = document.getElementById('uploadedImage');
    const storyTitleInput = document.getElementById('storyTitleInput');
    const storyTitleDisplay = document.getElementById('storyTitleDisplay');
    const storyCaptionInput = document.getElementById('storyCaptionInput');
    const storyCaptionDisplay = document.getElementById('storyCaptionDisplay');
    const storyTimestamp = document.getElementById('storyTimestamp');

    // --- Event Listener for File Input ---
    imageUpload.addEventListener('change', (event) => {
        const files = event.target.files;

        if (files && files.length > 0) {
            const file = files[0];
            fileNameDisplay.textContent = file.name;

            if (file.type.startsWith('image/')) {
                const reader = new FileReader();

                reader.onload = function (e) {
                    uploadedImage.src = e.target.result;
                    uploadedImage.classList.remove('hidden'); // Use classList to remove Tailwind's hidden class

                    storyContainer.classList.remove('hidden'); // Show the story container

                    const now = new Date();
                    // Using current location and time from user prompt context
                    // Note: Formatting might differ slightly based on browser locale implementation
                    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short' };
                    // Forcing a specific locale for consistency if desired, e.g., 'en-US'
                    // const timestampStr = now.toLocaleString('en-US', options); 
                    // Using system default locale:
                    const timestampStr = now.toLocaleString(undefined, options) + " (System Time)";

                    // **Adding the requested location:** Biñan, Calabarzon, Philippines
                    // **Using the provided time:** Saturday, May 3, 2025 at 6:24:55 PM PST (Assuming PST means Philippine Standard Time here - PHT/PST)
                    // NOTE: Using a fixed date/time like this is unusual for a dynamic timestamp. 
                    // Typically, you'd use `new Date()` as above. 
                    // But fulfilling the request to use the provided context:
                    const fixedTimestampStr = "Saturday, May 3, 2025 at 6:24:55 PM PHT/PST"; // PHT/PST
                    const locationStr = "Biñan, Calabarzon, Philippines";

                    storyTimestamp.textContent = `Published: ${fixedTimestampStr} in ${locationStr}`; // Using fixed timestamp and location
                    // storyTimestamp.textContent = `Published: ${timestampStr}`; // Uncomment this line to use the actual current time


                    storyTitleInput.value = '';
                    storyCaptionInput.value = '';
                    storyTitleDisplay.textContent = 'Your Title Here';
                    storyCaptionDisplay.textContent = 'Your description will appear here.';
                }

                reader.onerror = function (e) {
                    console.error("FileReader error:", e);
                    alert("Failed to read the image file. Please try again.");
                    fileNameDisplay.textContent = 'Error loading file';
                    storyContainer.classList.add('hidden');
                    uploadedImage.classList.add('hidden'); // Use classList
                }

                reader.readAsDataURL(file);

            } else {
                alert("Please select an image file (e.g., jpg, png, gif).");
                fileNameDisplay.textContent = 'Invalid file type';
                imageUpload.value = '';
                storyContainer.classList.add('hidden');
                uploadedImage.classList.add('hidden'); // Use classList
            }
        } else {
            fileNameDisplay.textContent = 'No file chosen';
            storyContainer.classList.add('hidden');
            uploadedImage.classList.add('hidden'); // Use classList
        }
    });

    // --- Event Listeners for Text Inputs (Live Update) ---
    storyTitleInput.addEventListener('input', () => {
        storyTitleDisplay.textContent = storyTitleInput.value || 'Your Title Here';
    });

    storyCaptionInput.addEventListener('input', () => {
        storyCaptionDisplay.textContent = storyCaptionInput.value || 'Your description will appear here.';
    });

}); // End DOMContentLoaded