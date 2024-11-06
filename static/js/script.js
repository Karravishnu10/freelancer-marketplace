function toggleMenu() {
  var menu = document.getElementById("hamburgerDropdown");
  if (menu.classList.contains("show")) {
    menu.classList.remove("show");
  } else {
    menu.classList.add("show");
  }
}
