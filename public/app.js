(() => {
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  const storage = {
    get(key, fallback) {
      try { const value = localStorage.getItem(key); return value === null ? fallback : JSON.parse(value); }
      catch { return fallback; }
    },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage may be unavailable */ } }
  };
  const state = {
    movies: [],
    cities: [],
    city: storage.get('reelhouse_city', 'Delhi NCR'),
    filter: 'All films',
    query: '',
    favorites: storage.get('reelhouse_favorites', []),
    booking: null,
    toastTimer: null
  };
  const imageFallbacks = [
    'linear-gradient(145deg,#26312b,#b3825d)', 'linear-gradient(145deg,#222d44,#db644b)',
    'linear-gradient(145deg,#151d36,#715bac)', 'linear-gradient(145deg,#242f43,#c77e73)',
    'linear-gradient(145deg,#354738,#bf986a)', 'linear-gradient(145deg,#554c3a,#e9b87f)',
    'linear-gradient(145deg,#273b48,#86a17d)', 'linear-gradient(145deg,#23252b,#898074)',
    'linear-gradient(145deg,#45574d,#d7a082)'
  ];
  const currency = value => '₹' + Number(value || 0).toLocaleString('en-IN');
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[char]));
  const movieById = id => state.movies.find(movie => movie.id === id);
  const durationText = mins => `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, '0')}m`;

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error || 'Something went wrong. Please try again.');
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function showToast(message, isFavorite = false) {
    const toast = $('#toast');
    toast.innerHTML = isFavorite ? `<span class="favorite-toast">✳</span> ${escapeHtml(message)}` : escapeHtml(message);
    toast.classList.add('visible');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove('visible'), 2450);
  }

  function renderHero() {
    const movie = state.movies.find(item => item.featured) || state.movies[0];
    if (!movie) return;
    $('#heroImage').style.backgroundImage = `url("${movie.cover}")`;
    $('#heroTitle').innerHTML = `${escapeHtml(movie.title)}<br><em>looks good here.</em>`;
    $('#heroDescription').textContent = movie.description;
    $('#heroLanguage').textContent = `${movie.language} · ${movie.genre}`.toUpperCase();
    $('#heroRating').innerHTML = `★ ${escapeHtml(movie.score)} <span class="muted-light">/ 10</span>`;
    $('#heroDuration').textContent = durationText(movie.duration);
    $('#heroGenres').textContent = movie.genres.join(' · ');
    $('#heroBook').dataset.bookMovie = movie.id;
    $('#heroTrailer').dataset.storyMovie = movie.id;
    const index = String(state.movies.indexOf(movie) + 1).padStart(2, '0');
    $('.hero-index-current').textContent = index;
    $('.hero-index').lastElementChild.textContent = String(state.movies.length).padStart(2, '0');
    $('#allCount').textContent = String(state.movies.length).padStart(2, '0');
  }

  function renderCities() {
    const menu = $('#cityMenu');
    menu.innerHTML = state.cities.map(city => `<button class="city-option ${city === state.city ? 'selected' : ''}" type="button" data-city="${escapeHtml(city)}">${escapeHtml(city)}</button>`).join('');
    $('#cityName').textContent = state.city;
  }

  function getVisibleMovies() {
    const query = state.query.trim().toLowerCase();
    return state.movies.filter(movie => {
      const matchesGenre = state.filter === 'All films' || movie.genres.includes(state.filter);
      const haystack = [movie.title, movie.language, movie.genre, ...movie.genres, ...movie.cast].join(' ').toLowerCase();
      return matchesGenre && (!query || haystack.includes(query));
    });
  }

  function renderMovies() {
    const movies = getVisibleMovies();
    const grid = $('#movieGrid');
    $('#emptyState').hidden = movies.length > 0;
    grid.hidden = movies.length === 0;
    $('#catalogueLabel').textContent = `Showing ${movies.length} ${movies.length === 1 ? 'hand-picked film' : 'hand-picked films'}`;
    grid.innerHTML = movies.map(movie => {
      const index = state.movies.indexOf(movie);
      const saved = state.favorites.includes(movie.id);
      return `<article class="movie-card">
        <div class="poster-wrap" style="background:${imageFallbacks[index % imageFallbacks.length]}">
          <img class="poster-image" src="${escapeHtml(movie.poster)}" alt="Cinematic artwork for ${escapeHtml(movie.title)}" loading="lazy">
          <div class="poster-gradient"></div>
          <span class="poster-badge">${escapeHtml(movie.badge)}</span>
          <button class="favorite-button ${saved ? 'saved' : ''}" data-favorite="${escapeHtml(movie.id)}" type="button" aria-label="${saved ? 'Remove ' + escapeHtml(movie.title) + ' from' : 'Add ' + escapeHtml(movie.title) + ' to'} saved films" aria-pressed="${saved}">${saved ? '♥' : '♡'}</button>
          <div class="poster-bottom"><span><span class="rating-star">★</span>${escapeHtml(movie.score)} <span style="color:rgba(255,255,255,.58)">(${escapeHtml(movie.reviews)})</span></span><span class="poster-format">${movie.language === 'English' ? 'SUB' : 'ORIGINAL'}</span></div>
        </div>
        <div class="movie-card-info"><div class="movie-card-title-row"><span class="movie-card-title">${escapeHtml(movie.title)}</span><span class="movie-card-language">${escapeHtml(movie.language.toUpperCase())}</span></div><div class="movie-card-subtitle">${escapeHtml(movie.genres.slice(0, 2).join(' · '))} <span>·</span> ${durationText(movie.duration)}</div><button class="book-inline" type="button" data-book-movie="${escapeHtml(movie.id)}">Get tickets from ${currency(movie.basePrice)} <span>↗</span></button></div>
      </article>`;
    }).join('');
    $$('.poster-image', grid).forEach(image => image.addEventListener('error', () => {
      image.style.display = 'none';
      image.parentElement.style.background = imageFallbacks[$$('.poster-image', grid).indexOf(image) % imageFallbacks.length];
    }, { once: true }));
  }

  function modalShell(kicker, title, body, steps = '') {
    const root = $('#modalRoot');
    root.hidden = false;
    root.innerHTML = `<section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <header class="modal-head"><div><div class="modal-kicker">${escapeHtml(kicker)}</div><h2 class="modal-title" id="modalTitle">${escapeHtml(title)}</h2></div><button class="modal-close" type="button" data-close-modal aria-label="Close dialog">×</button></header>
      ${steps}${body}
    </section>`;
    $('.modal-close', root).focus();
  }

  function closeModal() {
    const root = $('#modalRoot');
    root.hidden = true;
    root.innerHTML = '';
    state.booking = null;
  }

  function bookingSteps(active) {
    return `<div class="booking-steps">${[['01','Showtime'],['02','Seats'],['03','Checkout']].map((step,index) => {
      const value = index + 1;
      return `${index ? '<span class="step-line"></span>' : ''}<span class="step ${active === value ? 'active' : active > value ? 'done' : ''}"><span class="step-number">${active > value ? '✓' : step[0]}</span>${step[1]}</span>`;
    }).join('')}</div>`;
  }

  function movieStrip(movie) {
    return `<div class="booking-movie-strip"><img class="booking-movie-thumb" src="${escapeHtml(movie.poster)}" alt=""><div><strong>${escapeHtml(movie.title)}</strong><span>${escapeHtml(movie.language)} · ${escapeHtml(movie.rating)} · ${durationText(movie.duration)}</span></div><span class="booking-movie-spacer"></span><span class="booking-status">NOW SHOWING</span></div>`;
  }

  function dateOptions(selectedDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Array.from({ length: 7 }, (_, offset) => {
      const date = new Date(today);
      date.setDate(today.getDate() + offset);
      const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
      return { iso, dow: offset === 0 ? 'Today' : new Intl.DateTimeFormat('en-IN', { weekday: 'short' }).format(date), day: date.getDate() };
    }).map(day => `<button class="date-option ${day.iso === selectedDate ? 'active' : ''}" type="button" data-date="${day.iso}"><span>${day.dow}</span><span>${day.day}</span></button>`).join('');
  }

  function renderShowGroups() {
    if (state.booking.loadingShows) return '<div class="loading-line">Finding the best seats in your city…</div>';
    if (!state.booking.shows?.length) return '<div class="empty-shows">No showtimes for this date. Try another day or switch cities.</div>';
    const groups = new Map();
    state.booking.shows.forEach(show => {
      const key = `${show.cinema}|${show.area}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(show);
    });
    return [...groups.values()].map(shows => {
      const first = shows[0];
      return `<article class="cinema-group"><div class="cinema-header"><div><strong>${escapeHtml(first.cinema)}</strong><span>${escapeHtml(first.area)} · ${escapeHtml(first.city)}</span></div><span class="cinema-price">from ${currency(Math.min(...shows.map(show => show.price)))}</span></div><div class="format-labels">${first.formats.slice(0, 2).map(format => `<span>${escapeHtml(format)}</span>`).join('')}</div><div class="show-times">${shows.map(show => `<button class="show-time" type="button" data-show="${escapeHtml(show.id)}">${escapeHtml(show.time)}<small>${escapeHtml(show.formats[0])} · ${currency(show.price)}</small></button>`).join('')}</div></article>`;
    }).join('');
  }

  function renderBooking() {
    const booking = state.booking;
    if (!booking) return;
    const movie = booking.movie;
    if (booking.step === 1) {
      const body = `<div class="modal-content">${movieStrip(movie)}<span class="date-label">Pick a day that works</span><div class="date-list">${dateOptions(booking.date)}</div><span class="block-label">Showtimes near you · ${escapeHtml(state.city)}</span><div class="cinema-groups">${renderShowGroups()}</div></div>`;
      modalShell('MAKE IT A MOVIE NIGHT', 'Find the right showtime', body, bookingSteps(1));
      return;
    }
    if (booking.step === 2) {
      const show = booking.show;
      const available = booking.seatsData?.seats?.filter(seat => seat.status === 'available').length ?? 0;
      const seatButtons = (booking.seatsData?.seats || []).map((seat, index) => {
        const selected = booking.selectedSeats.includes(seat.id);
        const status = seat.status === 'sold' ? 'sold' : selected ? 'selected' : '';
        const aisle = index === 48 ? '<span class="seat-aisle" aria-hidden="true"></span>' : '';
        return `${aisle}<button class="seat ${status}" type="button" data-seat="${seat.id}" aria-label="Seat ${seat.id}, ${seat.status === 'sold' ? 'unavailable' : selected ? 'selected' : 'available'}" aria-pressed="${selected}" ${seat.status === 'sold' ? 'disabled' : ''}>${seat.number}</button>`;
      }).join('');
      const body = `<div class="modal-content">${movieStrip(movie)}<div class="seat-toolbar" style="margin-top:17px"><div class="seat-show-info"><strong>${escapeHtml(show.cinema)} · ${escapeHtml(show.area)}</strong><span>${escapeHtml(show.time)} · ${escapeHtml(show.date)} · ${escapeHtml(state.city)}</span></div><span class="seat-price-tag">${currency(show.price)} / seat</span></div>${booking.loadingSeats ? '<div class="loading-line">Checking seat availability…</div>' : `<div class="screen-wrap"><div class="screen"></div><div class="screen-caption">THE SCREEN IS THIS WAY</div></div><div class="seat-map" aria-label="Choose your seats">${seatButtons}</div><div class="seat-legend"><span><i class="legend-chip"></i>Available</span><span><i class="legend-chip selected"></i>Your seats</span><span><i class="legend-chip sold"></i>Taken</span></div><div class="seat-selection-note">${booking.selectedSeats.length ? `${booking.selectedSeats.length} seat${booking.selectedSeats.length > 1 ? 's' : ''} selected · ${available} still available` : `Select up to 8 seats · ${available} available`}</div>`}<div class="modal-actions"><button class="button button-outline" type="button" data-booking-back>← Change showtime</button><button class="button button-submit" type="button" data-booking-continue ${booking.selectedSeats.length ? '' : 'disabled'}>Continue <span>↗</span></button></div></div>`;
      modalShell('MAKE IT A MOVIE NIGHT', 'Choose your seats', body, bookingSteps(2));
      return;
    }
    if (booking.step === 3) {
      const show = booking.show;
      const base = show.price * booking.selectedSeats.length;
      const total = base + 39;
      const body = `<div class="modal-content"><div class="checkout-grid"><div class="form-stack"><form id="checkoutForm" novalidate><div class="form-stack"><label class="field-label">YOUR NAME<input name="name" type="text" placeholder="As on your ticket" minlength="2" maxlength="80" autocomplete="name" required></label><label class="field-label">EMAIL ADDRESS<input name="email" type="email" placeholder="For your booking confirmation" autocomplete="email" required></label><label class="field-label">PHONE NUMBER<input name="phone" type="tel" placeholder="+91 98765 43210" autocomplete="tel" required></label><div class="field-label">HOW WOULD YOU LIKE TO PAY?<div class="payment-options"><button class="payment-option active" type="button" data-pay="cinema">Pay at cinema</button><button class="payment-option" type="button" data-pay="upi-demo">UPI · demo</button></div></div></div></form></div><aside class="order-summary"><div class="summary-label">YOUR MOVIE NIGHT</div><div class="summary-movie">${escapeHtml(movie.title)}</div><div class="summary-details">${escapeHtml(show.cinema)} · ${escapeHtml(show.area)}<br>${escapeHtml(show.date)} at ${escapeHtml(show.time)}<br>${escapeHtml(state.city)}</div><div class="summary-seats">Seats ${booking.selectedSeats.join(', ')}</div><div class="summary-row"><span>${booking.selectedSeats.length} ticket${booking.selectedSeats.length > 1 ? 's' : ''} × ${currency(show.price)}</span><span>${currency(base)}</span></div><div class="summary-row"><span>Convenience fee</span><span>${currency(39)}</span></div><div class="summary-row total"><span>Total</span><span>${currency(total)}</span></div></aside></div><div id="checkoutError" aria-live="polite"></div><div class="modal-actions"><button class="button button-outline" type="button" data-booking-back>← Change seats</button><button class="button button-submit" type="submit" form="checkoutForm" id="confirmBooking">Reserve seats · ${currency(total)} <span>↗</span></button></div><div class="small-note">UPI is a demo selection; no real payment is collected.</div></div>`;
      modalShell('ONE LAST THING', 'Make it official', body, bookingSteps(3));
      return;
    }
    if (booking.step === 'success') {
      const confirmation = booking.confirmation;
      const paymentLabel = confirmation.paymentMethod === 'UPI (demo)' ? 'UPI demo · not charged' : 'Pay at cinema';
      const body = `<div class="confirmation"><div class="confirmation-mark">✓</div><h2>Your seats are waiting.</h2><p>We’ve saved you the good seats. Your booking reference is ready below—keep it handy when you arrive.</p><div class="ticket-card"><img class="ticket-card-poster" src="${escapeHtml(movie.poster)}" alt=""><div class="ticket-card-info"><strong>${escapeHtml(movie.title)}</strong><span>${escapeHtml(confirmation.show.cinema)} · ${escapeHtml(confirmation.show.area)}<br>${escapeHtml(confirmation.show.date)} · ${escapeHtml(confirmation.show.time)}<br>Seats ${confirmation.seats.join(', ')}</span></div><span class="ticket-code">${escapeHtml(confirmation.id)}</span></div><div class="ticket-total"><span>${paymentLabel}</span><strong>${currency(confirmation.total)}</strong></div><div class="confirmation-actions"><button class="button button-outline" type="button" data-print-ticket>Print ticket</button><button class="button button-submit" type="button" data-my-ticket="${escapeHtml(confirmation.id)}">Save this ticket <span>↗</span></button></div><div class="small-note">A copy of your booking details is saved in this browser.</div></div>`;
      modalShell('BOOKING CONFIRMED', 'A very good night, indeed.', body);
    }
  }

  async function loadShows() {
    const booking = state.booking;
    if (!booking) return;
    booking.loadingShows = true;
    renderBooking();
    try {
      booking.shows = await api(`/api/shows?movieId=${encodeURIComponent(booking.movieId)}&date=${encodeURIComponent(booking.date)}&city=${encodeURIComponent(state.city)}`);
    } catch (error) {
      booking.shows = [];
      showToast(error.message);
    } finally {
      booking.loadingShows = false;
      if (state.booking === booking) renderBooking();
    }
  }

  async function openBooking(movieId) {
    const movie = movieById(movieId);
    if (!movie) return;
    const date = new Date();
    const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    state.booking = { movieId, movie, date: iso, step: 1, shows: [], loadingShows: true, selectedSeats: [], payMethod: 'cinema' };
    renderBooking();
    await loadShows();
  }

  async function chooseShow(showId) {
    const booking = state.booking;
    if (!booking) return;
    const show = booking.shows.find(item => item.id === showId);
    if (!show) return;
    booking.show = show;
    booking.selectedSeats = [];
    booking.seatsData = null;
    booking.loadingSeats = true;
    booking.step = 2;
    renderBooking();
    try {
      booking.seatsData = await api(`/api/seats?showId=${encodeURIComponent(showId)}`);
    } catch (error) {
      showToast(error.message);
      booking.step = 1;
    } finally {
      booking.loadingSeats = false;
      if (state.booking === booking) renderBooking();
    }
  }

  function localTickets() {
    return storage.get('reelhouse_tickets', []);
  }

  function rememberTicket(booking) {
    const tickets = localTickets().filter(item => item.id !== booking.id);
    tickets.unshift({ id: booking.id, email: booking.email });
    storage.set('reelhouse_tickets', tickets.slice(0, 10));
  }

  function renderLookup(kicker, title, initialCode = '', initialEmail = '') {
    const body = `<div class="lookup-wrap"><div class="lookup-icon">✳</div><h2>Your plans, right here.</h2><p>Enter the booking reference and the email you used to reserve your seats.</p><form class="lookup-form" id="lookupForm"><input type="text" name="reference" placeholder="BOOKING REFERENCE" aria-label="Booking reference" maxlength="24" value="${escapeHtml(initialCode)}" required><input type="email" name="email" placeholder="EMAIL ADDRESS" aria-label="Booking email" value="${escapeHtml(initialEmail)}" required><button class="button button-submit" type="submit">Find my ticket ↗</button></form><div class="lookup-result" id="lookupResult"></div></div>`;
    modalShell(kicker, title, body);
  }

  function openMyTickets() {
    const recent = localTickets()[0] || { id: '', email: '' };
    renderLookup('YOUR REELHOUSE', 'My tickets', recent.id, recent.email);
  }

  function renderTicketResult(booking) {
    const result = $('#lookupResult');
    if (!result) return;
    const isCancelled = booking.status === 'Cancelled';
    result.innerHTML = `<article class="lookup-ticket"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><h3>${escapeHtml(booking.movieTitle)}</h3><span class="booking-status ${isCancelled ? 'cancelled' : ''}">${escapeHtml(booking.status)}</span></div><p>${escapeHtml(booking.show.cinema)} · ${escapeHtml(booking.show.area)} · ${escapeHtml(booking.show.city)}</p><p>${escapeHtml(booking.show.date)} at ${escapeHtml(booking.show.time)}</p><p>Seats ${booking.seats.map(escapeHtml).join(', ')}</p><div class="lookup-ticket-foot"><span>Ref. ${escapeHtml(booking.id)}</span><strong>${currency(booking.total)}</strong></div>${isCancelled ? '' : `<button class="cancel-link" type="button" data-cancel-booking="${escapeHtml(booking.id)}">Cancel this reservation</button>`}</article>`;
  }

  function openStory(movieId) {
    const movie = movieById(movieId);
    if (!movie) return;
    const body = `<div class="trailer-panel"><div class="trailer-visual" style="--trailer-image:url('${escapeHtml(movie.cover)}')"><span class="trailer-play">✳</span></div><p class="trailer-caption">${escapeHtml(movie.description)}<br><br><strong>Starring</strong> ${movie.cast.map(escapeHtml).join(' · ')}<br>${escapeHtml(movie.language)} · ${escapeHtml(movie.rating)} · ${durationText(movie.duration)}</p><button class="button button-submit" type="button" data-book-movie="${escapeHtml(movie.id)}">Find a showtime <span>↗</span></button></div>`;
    modalShell('A NOTE ABOUT THE FILM', movie.title, body);
  }

  $('#filterPills').addEventListener('click', event => {
    const button = event.target.closest('[data-filter]');
    if (!button) return;
    state.filter = button.dataset.filter;
    $$('.filter-pill').forEach(pill => pill.classList.toggle('active', pill === button));
    renderMovies();
  });
  $('#movieSearch').addEventListener('input', event => { state.query = event.target.value; renderMovies(); });
  $('#resetFilters').addEventListener('click', () => {
    state.query = '';
    state.filter = 'All films';
    $('#movieSearch').value = '';
    $$('.filter-pill').forEach(pill => pill.classList.toggle('active', pill.dataset.filter === 'All films'));
    renderMovies();
  });
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); $('#movieSearch').focus(); }
    if (event.key === 'Escape' && !$('#modalRoot').hidden) closeModal();
  });
  $('#cityButton').addEventListener('click', () => {
    const menu = $('#cityMenu');
    menu.hidden = !menu.hidden;
    $('#cityButton').setAttribute('aria-expanded', String(!menu.hidden));
  });
  $('#cityMenu').addEventListener('click', event => {
    const button = event.target.closest('[data-city]');
    if (!button) return;
    state.city = button.dataset.city;
    storage.set('reelhouse_city', state.city);
    renderCities();
    $('#cityMenu').hidden = true;
    $('#cityButton').setAttribute('aria-expanded', 'false');
    showToast(`Showing cinema nights in ${state.city}`);
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('#cityButton, #cityMenu')) {
      $('#cityMenu').hidden = true;
      $('#cityButton').setAttribute('aria-expanded', 'false');
    }
  });
  $('#myBookingsButton').addEventListener('click', openMyTickets);
  $('#heroBook').addEventListener('click', event => openBooking(event.currentTarget.dataset.bookMovie));
  $('#heroTrailer').addEventListener('click', event => openStory(event.currentTarget.dataset.storyMovie));

  document.addEventListener('click', async event => {
    const favorite = event.target.closest('[data-favorite]');
    if (favorite) {
      const movieId = favorite.dataset.favorite;
      const saved = state.favorites.includes(movieId);
      state.favorites = saved ? state.favorites.filter(id => id !== movieId) : [...state.favorites, movieId];
      storage.set('reelhouse_favorites', state.favorites);
      renderMovies();
      const movie = movieById(movieId);
      showToast(`${movie.title} ${saved ? 'removed from' : 'saved to'} your list`, true);
      return;
    }
    const bookButton = event.target.closest('[data-book-movie]');
    if (bookButton) {
      const movieId = bookButton.dataset.bookMovie;
      closeModal();
      await openBooking(movieId);
      return;
    }
    const dateButton = event.target.closest('[data-date]');
    if (dateButton && state.booking?.step === 1) {
      if (state.booking.date !== dateButton.dataset.date) {
        state.booking.date = dateButton.dataset.date;
        state.booking.show = null;
        await loadShows();
      }
      return;
    }
    const showButton = event.target.closest('[data-show]');
    if (showButton && state.booking?.step === 1) { await chooseShow(showButton.dataset.show); return; }
    const seatButton = event.target.closest('[data-seat]');
    if (seatButton && state.booking?.step === 2 && !seatButton.disabled) {
      const selected = state.booking.selectedSeats;
      const seatId = seatButton.dataset.seat;
      if (selected.includes(seatId)) state.booking.selectedSeats = selected.filter(seat => seat !== seatId);
      else if (selected.length >= 8) showToast('You can choose up to 8 seats in one booking.');
      else state.booking.selectedSeats = [...selected, seatId];
      renderBooking();
      return;
    }
    if (event.target.closest('[data-booking-back]')) {
      if (!state.booking) return;
      state.booking.step = state.booking.step === 3 ? 2 : 1;
      renderBooking();
      return;
    }
    if (event.target.closest('[data-booking-continue]')) {
      if (state.booking?.selectedSeats.length) { state.booking.step = 3; renderBooking(); }
      return;
    }
    const payment = event.target.closest('[data-pay]');
    if (payment) {
      state.booking.payMethod = payment.dataset.pay;
      $$('.payment-option').forEach(option => option.classList.toggle('active', option === payment));
      return;
    }
    if (event.target.closest('[data-close-modal]') || (event.target === $('#modalRoot'))) { closeModal(); return; }
    if (event.target.closest('[data-print-ticket]')) { window.print(); return; }
    const viewTicket = event.target.closest('[data-my-ticket]');
    if (viewTicket) {
      const saved = state.booking.confirmation;
      closeModal();
      renderLookup('YOUR REELHOUSE', 'My tickets', saved.id, saved.email);
      const form = $('#lookupForm');
      if (form) {
        const result = $('#lookupResult');
        result.innerHTML = '<div class="loading-line">Opening your ticket…</div>';
        try { renderTicketResult(await api(`/api/bookings/${encodeURIComponent(saved.id)}?email=${encodeURIComponent(saved.email)}`)); }
        catch (error) { result.innerHTML = `<div class="modal-error">${escapeHtml(error.message)}</div>`; }
      }
      return;
    }
    const cancelButton = event.target.closest('[data-cancel-booking]');
    if (cancelButton) {
      const form = $('#lookupForm');
      const email = new FormData(form).get('email');
      if (!window.confirm('Cancel this reservation? Your seats will become available again.')) return;
      try {
        const booking = await api(`/api/bookings/${encodeURIComponent(cancelButton.dataset.cancelBooking)}/cancel`, { method: 'POST', body: JSON.stringify({ email }) });
        renderTicketResult(booking);
        showToast('Your booking has been cancelled.');
      } catch (error) {
        $('#lookupResult').insertAdjacentHTML('afterbegin', `<div class="modal-error">${escapeHtml(error.message)}</div>`);
      }
    }
  });

  document.addEventListener('submit', async event => {
    if (event.target.id === 'checkoutForm') {
      event.preventDefault();
      const form = event.target;
      const errorSlot = $('#checkoutError');
      errorSlot.innerHTML = '';
      if (!form.reportValidity()) return;
      const data = new FormData(form);
      const button = $('#confirmBooking');
      button.disabled = true;
      button.textContent = 'Saving your seats…';
      try {
        const booking = await api('/api/bookings', {
          method: 'POST',
          body: JSON.stringify({
            movieId: state.booking.movieId,
            showId: state.booking.show.id,
            seats: state.booking.selectedSeats,
            name: data.get('name'),
            email: data.get('email'),
            phone: data.get('phone'),
            paymentMethod: state.booking.payMethod
          })
        });
        rememberTicket(booking);
        state.booking.confirmation = booking;
        state.booking.step = 'success';
        renderBooking();
      } catch (error) {
        errorSlot.innerHTML = `<div class="modal-error">${escapeHtml(error.message)}</div>`;
        button.disabled = false;
        const total = state.booking.show.price * state.booking.selectedSeats.length + 39;
        button.innerHTML = `Reserve seats · ${currency(total)} <span>↗</span>`;
      }
      return;
    }
    if (event.target.id === 'lookupForm') {
      event.preventDefault();
      const data = new FormData(event.target);
      const id = String(data.get('reference') || '').trim().toUpperCase();
      const email = String(data.get('email') || '').trim().toLowerCase();
      const result = $('#lookupResult');
      result.innerHTML = '<div class="loading-line">Looking up your ticket…</div>';
      try {
        const booking = await api(`/api/bookings/${encodeURIComponent(id)}?email=${encodeURIComponent(email)}`);
        const remembered = localTickets();
        if (!remembered.some(item => item.id === booking.id)) { remembered.unshift({ id: booking.id, email }); storage.set('reelhouse_tickets', remembered.slice(0, 10)); }
        renderTicketResult(booking);
      } catch (error) { result.innerHTML = `<div class="modal-error">${escapeHtml(error.message)}</div>`; }
      return;
    }
    if (event.target.id === 'offerForm') {
      event.preventDefault();
      const form = event.target;
      const email = $('#offerEmail').value.trim();
      const button = $('button[type="submit"]', form);
      button.disabled = true;
      try {
        await api('/api/newsletter', { method: 'POST', body: JSON.stringify({ email }) });
        $('#offerNote').textContent = 'You’re on the list. Good films, occasional notes. That’s it.';
        form.reset();
      } catch (error) {
        $('#offerNote').textContent = error.message;
      } finally { button.disabled = false; }
    }
  });

  async function init() {
    try {
      const [movies, cities] = await Promise.all([api('/api/movies'), api('/api/cities')]);
      state.movies = movies;
      state.cities = cities;
      if (!cities.includes(state.city)) state.city = cities[0] || 'Delhi NCR';
      renderCities();
      renderHero();
      renderMovies();
    } catch (error) {
      $('#movieGrid').hidden = true;
      $('#emptyState').hidden = false;
      $('#emptyState').innerHTML = `<span>✳</span><h3>Reelhouse is taking a quick breather.</h3><p>${escapeHtml(error.message)} Make sure the local server is running, then refresh.</p>`;
      showToast('Start the Reelhouse server to load the movies.');
    }
  }
  init();
})();
