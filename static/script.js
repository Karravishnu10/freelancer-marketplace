document.addEventListener("DOMContentLoaded", function () {
  const rangeInput = document.getElementById("max-rate");
  const rangeValueDisplay = document.createElement("span");
  rangeValueDisplay.textContent = ` $${rangeInput.value}/hr`;
  rangeInput.parentNode.insertBefore(rangeValueDisplay, rangeInput.nextSibling);

  rangeInput.oninput = function () {
    rangeValueDisplay.textContent = ` $${this.value}/hr`;
  };

  // Assume a form submission function to load freelancers
  document.querySelector("form").onsubmit = function (event) {
    event.preventDefault();
    loadFreelancers(); // You'll define this function to actually load freelancers based on the form data
  };

  function loadFreelancers() {
    // Placeholder for AJAX request to load freelancers
    console.log("Search initiated...");
    // Here you'd typically make an AJAX request to your server to fetch freelancer data
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const searchForm = document.querySelector("form");
  searchForm.onsubmit = function (event) {
    event.preventDefault();
    loadJobs(); // Function to fetch and display jobs based on the search criteria
  };
});

function loadJobs() {
  console.log("Fetching jobs based on filters...");
  // Here you'd make an AJAX call to your server to fetch jobs
  // For now, it's just logging to the console
}

function sendMessage() {
  const messageText = document.getElementById("message-text").value;
  console.log("Message sent:", messageText);
  // Append message to messages div
  const messagesDiv = document.getElementById("messages");
  const newMessage = document.createElement("div");
  newMessage.textContent = messageText;
  messagesDiv.appendChild(newMessage);
  document.getElementById("message-text").value = ""; // Clear input
}

function sendVoiceMessage() {
  console.log("Voice message sent");
  // Implement functionality or API integration for sending voice messages
}
