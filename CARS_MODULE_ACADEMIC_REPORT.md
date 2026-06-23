# Technical and Academic Report for the `/cars` Module

## 1. Title

**Technical Analysis of the Car Rental, Booking, Mapping, Pricing, and Payment Subsystem in the Allen Bus Management Project**

## 2. Scope of This Report

This report analyzes the `"/allen/cars/"` module and all closely related components that participate in private car rental inside the project. The analysis is based on the current source code state in the repository and focuses on:

- The car catalog layer.
- The car details and booking interface.
- The map subsystem.
- The pricing logic.
- The payment workflow.
- The database models.
- The admin layer.
- The algorithms currently used.
- The technical limitations and risks that should be acknowledged in an academic submission.

This report is intentionally written in an academic and engineering-oriented style so that it can be adapted into a graduation-project chapter, system-analysis chapter, or implementation chapter.

## 3. Project Context

The repository is a large Django-based transportation platform. Its main business scope is bus and trip management, but it also contains a private car rental subsystem. The `/cars` module is therefore not a separate application; it is a subsystem implemented inside the main Django app `Anaconda_bus_APP`.

At the architectural level, the car module behaves as a semi-independent workflow with its own:

- Catalog pages.
- Rental booking model.
- Map-based origin/destination selection.
- Dynamic price estimation.
- Payment gateway integration.
- Customer and driver notification flow.

## 4. Main Files Related to the `/cars` Subsystem

The core implementation is distributed across the following files:

- `Anaconda_bus_APP/models.py`
- `Anaconda_bus_APP/views.py`
- `Anaconda_bus_APP/urls.py`
- `Anaconda_bus_APP/forms.py`
- `Anaconda_bus_APP/admin.py`
- `Anaconda_bus_APP/templates/car_list.html`
- `Anaconda_bus_APP/templates/car_detail.html`
- `Anaconda_bus_APP/templates/car_booking.html`
- `Anaconda_bus_APP/templates/map_selection.html`
- `Anaconda_bus_APP/templates/success.html`
- `Main_Bus_Management/settings.py`
- `SELF_HOSTED_MAPS.md`
- `docker-compose.yml`
- `requirements.txt`

## 5. Routing and Entry Points

The user-facing entry points for the car subsystem are registered in `Anaconda_bus_APP/urls.py`.

The most important routes are:

- `/allen/cars/` -> car list page.
- `/allen/car/<car_id>/` -> car details and booking page.
- `/allen/api/maps/search/` -> place autocomplete backend.
- `/allen/api/maps/reverse/` -> reverse geocoding backend.
- `/allen/api/maps/route/` -> driving route and distance backend.
- `/allen/create_car_payment/` -> AJAX endpoint to create a pending car booking and return a payment URL.
- `/allen/car/payment/success/` -> payment return endpoint.
- `/allen/car/payment/failed/` -> failure return endpoint.
- `/allen/car-booking-success/` -> legacy booking success flow.

## 6. Technology Stack Used by the `/cars` Module

### 6.1 Backend Technologies

- Python 3.11
- Django 5.0.7
- PostgreSQL
- Django Admin
- Django templates
- Requests library for outbound HTTP calls

### 6.2 Frontend Technologies

- HTML
- CSS
- Vanilla JavaScript
- Leaflet
- MapLibre GL
- Pannellum for 360-degree panorama viewing
- Font Awesome
- Google Fonts

### 6.3 Mapping Technologies

The current implementation does not rely on Google Maps in the active booking page. Instead, it uses:

- Self-hosted or public tiles for base-map rendering.
- Photon for search autocomplete when available.
- Nominatim for fallback geocoding and reverse geocoding.
- OSRM for driving route calculation.
- Valhalla as a routing fallback.

### 6.4 Payment and Messaging

- Kashier payment gateway
- UltraMsg WhatsApp integration

### 6.5 Deployment and Runtime Context

Although the `/cars` module is a web-facing feature, it runs inside the wider project infrastructure:

- `web` service for Django application execution
- `db` service for PostgreSQL persistence
- `redis` service for background-job support
- `celery_worker` for asynchronous tasks in the broader platform
- `celery_beat` for scheduled jobs in the broader platform

The car subsystem itself does not require Celery for its immediate booking flow, but it benefits from being hosted inside a system that already supports background processing and operational scalability.

## 6.6 Configuration Variables Relevant to the Car Subsystem

The following settings directly affect the `/cars` workflow:

- `KASHIER_API_KEY`
- `KASHIER_SECRET_KEY`
- `KASHIER_ACCOUNT_KEY`
- `KASHIER_MODE`
- `ULTRAMSG_INSTANCE_ID`
- `ULTRAMSG_API_TOKEN`
- `SELF_HOSTED_MAP_STYLE_URL`
- `SELF_HOSTED_MAP_DARK_STYLE_URL`
- `SELF_HOSTED_TILE_URL`
- `SELF_HOSTED_TILE_ATTRIBUTION`
- `SELF_HOSTED_PHOTON_URL`
- `SELF_HOSTED_NOMINATIM_URL`
- `SELF_HOSTED_OSRM_URL`
- `SELF_HOSTED_VALHALLA_URL`
- `PUBLIC_PHOTON_URL`
- `PUBLIC_OSRM_URL`

### Academic interpretation

This subsystem is not self-contained in a purely local sense. It is a configurable service-oriented module whose runtime behavior changes according to deployment-time environment variables.

## 7. High-Level Architecture of the Car Module

The subsystem follows a multi-layer web architecture:

1. Presentation layer:
   `car_list.html` and `car_detail.html` render the user experience.

2. Client-side interaction layer:
   JavaScript in `car_detail.html` manages map interaction, route selection, price estimation, state persistence, and the AJAX payment request.

3. View/controller layer:
   Django view functions in `views.py` receive page requests and API requests.

4. Domain/data layer:
   Django models `Car`, `CarImage`, `GeoBooking`, and `CarBooking` define the persistent entities.

5. Infrastructure/services layer:
   External services provide routing, geocoding, payment processing, and WhatsApp messaging.

This architecture is hybrid: part of the business logic is executed in Django, while an important portion of the user workflow is executed in the browser.

## 8. Data Model Analysis

## 8.1 `Car` Model

The `Car` model represents a rentable vehicle. It stores:

- Identity fields:
  - `name`
  - `model`
  - `brand`

- Operational field:
  - `car_driver_number`

- Vehicle specification fields:
  - `transmission`
  - `seats`

- Distance-based pricing slabs:
  - `price_per_km_0_100`
  - `price_per_km_101_200`
  - `price_per_km_201_300`
  - `price_per_km_301_400`
  - `price_per_km_401_500`
  - `price_per_km_501_600`
  - `price_per_km_601_700`
  - `price_per_km_701_800`
  - `price_per_km_801_900`
  - `price_per_km_901_1000`
  - `price_per_km_above_1000`

- Fixed-price services:
  - `DAY_USE`
  - `day_use_12_price`
  - `day_use_10_price`
  - `day_use_8_price`
  - `airport_pickup_price`

- Media fields:
  - `image`
  - `panorama_image`
  - `description`

- Availability field:
  - `is_available`

### Academic interpretation

This model implements a **vehicle catalog plus tariff configuration**. The important design choice is that each car stores its own tariff slab table instead of referencing a separate pricing table. This simplifies querying and rendering, but it increases schema width and can make tariff maintenance harder if many vehicles share the same pricing policy.

## 8.2 `CarImage` Model

`CarImage` stores additional images related to a car:

- `car`
- `image`

This supports a gallery-like representation for multiple views of the same vehicle.

## 8.3 `GeoBooking` Model

`GeoBooking` contains:

- `car`
- `user`
- `pickup_location`
- `dropoff_location`
- `distance_km`
- `total_price`
- `booking_date`

### Technical note

This model is not part of the active booking flow used by the modern `car_detail.html` page. It appears to be an older or experimental persistence model for geospatial bookings.

## 8.4 `CarBooking` Model

`CarBooking` is the primary booking entity for the active private car rental workflow.

Its major fields are:

- Booking identity and status:
  - `status`
  - `created_at`
  - `merchant_order_id`

- Customer data:
  - `customer_name`
  - `phone_number`

- Service classification:
  - `trip_type`
  - `payment_percentage`

- Time data:
  - `go_date`
  - `return_date`
  - `go_time`
  - `back_time`

- Route data:
  - `from_location`
  - `to_location`
  - `distance_km`

- Financial data:
  - `total_price`
  - `paid_amount`

- Foreign key:
  - `car`

### Trip types supported

The model supports the following service types:

- `one_way_go`
- `one_way_return`
- `round_trip`
- `day_use`
- `day_use_12`
- `day_use_10`
- `day_use_8`
- `airport_pickup`

### Payment percentages supported

- `100`
- `50`

This means the system supports both full prepayment and partial prepayment.

## 9. URL-to-Function Mapping

### 9.1 Car list

Function:

- `car_list(request)`

Responsibilities:

- Query available models.
- Optionally filter cars by model.
- Render the catalog page.

### 9.2 Car detail

Function:

- `car_detail(request, car_id)`

Responsibilities:

- Load the selected car.
- Prepare comparison data for all cars.
- Render the map-driven booking UI.
- Expose pricing data to JavaScript.

### 9.3 Map search

Function:

- `map_search(request)`

Responsibilities:

- Accept text input.
- Query Photon or Nominatim.
- Return normalized JSON search results.

### 9.4 Reverse geocoding

Function:

- `map_reverse(request)`

Responsibilities:

- Accept latitude and longitude.
- Query Photon or Nominatim.
- Return a normalized place object.

### 9.5 Routing

Function:

- `map_route(request)`

Responsibilities:

- Accept origin and destination coordinates.
- Call OSRM first.
- Fall back to Valhalla if needed.
- Return distance, duration, and geometry.

### 9.6 Payment initialization

Function:

- `create_car_payment(request)`

Responsibilities:

- Validate booking payload.
- Check overlap with existing bookings.
- Create a pending `CarBooking`.
- Generate a Kashier checkout URL.
- Return JSON containing the checkout URL.

### 9.7 Payment callback/return

Function:

- `car_payment_success(request)`

Responsibilities:

- Read payment result from GET parameters.
- Mark the booking as confirmed when payment succeeded.
- Notify customer and driver through WhatsApp.
- Render the success page.

## 10. Functional Workflow of the Current Car Booking System

The active production-style flow is not a classical server-rendered form submission. It is a **map-centric interactive flow**.

### 10.1 End-to-End Data Flow Summary

The end-to-end control flow can be summarized as:

1. Browser requests `/allen/cars/`
2. Django renders car catalog
3. Browser requests `/allen/car/<car_id>/`
4. Django embeds car pricing data and map configuration into the page
5. JavaScript captures route and booking choices
6. JavaScript calls map APIs for search, reverse geocoding, and routing
7. JavaScript computes estimated pricing locally
8. JavaScript submits a payment-initialization payload to Django
9. Django creates `CarBooking(status="pending")`
10. Django generates Kashier checkout URL
11. Browser redirects to Kashier
12. Kashier returns to Django success/failure URL
13. Django updates booking state and sends notifications

### Step 1: Catalog browsing

The user visits `/allen/cars/`.

The backend:

- Reads an optional `category` query parameter.
- Interprets that value as a `model` filter.
- Loads cars.
- Renders the list.

### Step 2: Opening a vehicle page

The user selects a car and visits `/allen/car/<car_id>/`.

The backend:

- Loads the target car.
- Serializes all comparable cars into JSON.
- Injects map configuration values into the template.

### Step 3: Defining the trip

Inside the detail page, the user:

- Chooses a trip type.
- Chooses departure and possibly return dates.
- Optionally chooses times.
- Selects origin and destination via:
  - text search
  - map click
  - device geolocation
  - center-pin selection mode

### Step 4: Computing the route

When both points are available, the frontend calls `/allen/api/maps/route/`.

The backend:

- Sends coordinates to OSRM.
- If OSRM fails, tries Valhalla.
- Returns:
  - `distance_km`
  - `duration_min`
  - polyline geometry

The frontend then:

- Draws the route.
- Displays trip distance and estimated duration.
- Recomputes the price.

### Step 5: Client-side price estimation

The page calculates the price immediately in JavaScript using per-car tariff data already embedded in the page.

### Step 6: Comparison ranking

The system recalculates the same trip against all cars and ranks them by estimated price. This supports decision making and cross-selling.

### Step 7: Payment request

When the user clicks the payment button, the browser sends a JSON payload to `/allen/create_car_payment/`.

The backend:

- Validates payload completeness.
- Checks date overlap.
- Creates a pending booking.
- Generates a Kashier checkout URL.

### Step 8: Payment return

After checkout, Kashier redirects the user back to the system.

If `paymentStatus=SUCCESS`:

- The booking becomes `confirmed`.
- Customer WhatsApp confirmation is sent.
- Driver WhatsApp notification is sent.

## 11. Frontend Design and Interaction Model

The current `car_detail.html` page is significantly more advanced than a traditional HTML booking form.

Its interface combines:

- A full-screen map canvas.
- A mobile bottom-sheet interaction model.
- Rich route input widgets.
- Real-time price estimation.
- Cross-car comparison.
- Panorama viewing when available.

### 11.1 Bottom-sheet state machine

On mobile screens, the interface behaves like a ride-hailing application. The bottom sheet has multiple states:

- `expanded`
- `half`
- `docked`

JavaScript manages:

- drag start
- drag move
- drag end
- nearest-state snapping
- dynamic viewport recalculation

This is effectively a lightweight UI state machine implemented manually in vanilla JavaScript.

### 11.2 State persistence

The page preserves state in two ways:

- Query string state:
  - route points
  - trip type
  - dates
  - times
  - payment percentage

- `sessionStorage`:
  - private user draft data such as name and phone number

This makes the workflow resilient when the user switches to another car during comparison.

## 12. Map Subsystem Architecture

The mapping subsystem is one of the most technically interesting parts of the car module.

## 12.1 Why the project does not depend on Google Maps in the active flow

The current implementation intentionally uses open mapping infrastructure and self-hosted options. This reduces:

- external API key dependency
- long-term vendor lock-in
- operating cost under heavy usage

## 12.2 Search endpoint behavior

The search endpoint:

- requires a minimum query length of 2 characters
- accepts an optional location bias through `lat` and `lng`
- restricts results to Egypt through a geographic bounding box
- uses Photon first
- falls back to Nominatim

### Output normalization

The backend converts provider-specific payloads into a unified result format:

- `label`
- `lat`
- `lng`
- `display_name`
- `governorate`
- `source`
- `country_code`

This is a clean adapter-layer design.

## 12.3 Reverse geocoding behavior

The reverse endpoint:

- validates coordinates
- asks Photon first
- falls back to Nominatim
- returns one normalized place object

If both services fail, the frontend can still continue using a fallback coordinate-based label. This improves robustness.

## 12.4 Routing endpoint behavior

The routing endpoint:

- validates four numeric coordinates
- queries OSRM first
- falls back to Valhalla
- returns:
  - route distance in kilometers
  - route duration in minutes
  - geometry array
  - provider name

### Academic interpretation

The repository itself does not implement shortest-path routing over a road graph. Instead, it delegates that responsibility to specialized routing engines. Therefore, the application-layer contribution is:

- routing-service orchestration
- fallback management
- payload normalization
- client visualization

## 13. Algorithms Used in the Car Module

This section explains the practical algorithms used inside the current implementation.

## 13.1 Catalog filtering algorithm

Used in `car_list`.

Logic:

- Retrieve distinct values of `Car.model`.
- If a `category` query parameter exists, filter cars where `model == category`.
- Otherwise show all cars.

### Complexity

- Distinct model extraction depends on the database engine.
- Car filtering is a database-level selection operation.

### Observation

The variable name `category` is semantically misleading because it actually stores a car model filter.

## 13.2 Search debounce algorithm

Used in the browser for text place search.

Logic:

- After each keystroke, cancel the previous timer.
- Wait `280 ms`.
- Send only the latest search request.

### Purpose

- Reduce unnecessary network calls.
- Improve UI responsiveness.
- Prevent flooding the geocoding backend.

### Complexity

- O(1) per input event locally.
- Server-side cost depends on the external geocoder.

## 13.3 Place resolution algorithm

Used in `ensurePointResolved(type)`.

Logic:

- If the text box matches the current stored point, do nothing.
- Otherwise call the search API with the typed value.
- Use the first match.
- Convert it into the internal point object.

### Academic interpretation

This is a lightweight **text-to-entity resolution** strategy. It does not implement ranking itself; it trusts the provider ranking and selects the first candidate.

## 13.4 Route drawing algorithm

Used in `drawRoute()`.

Logic:

- If either endpoint is missing, clear the route.
- Otherwise call the route endpoint.
- Draw a glow polyline and a main polyline.
- Update distance and duration.
- Refit the map viewport.
- Trigger price recalculation.

### Academic interpretation

This is a **reactive route-rendering pipeline** rather than a mathematical routing algorithm implemented inside the repository.

## 13.5 Slab-based pricing algorithm

Used in `calculateEstimateForCar(carData, selectedType, tripDistance)`.

Logic:

- For fixed-price trip types:
  - return the corresponding fixed tariff

- For distance-based trip types:
  - choose the first distance slab whose `max` value contains the trip distance
  - multiply distance by slab rate
  - if trip type is `round_trip`, multiply by 2
  - if trip type is `day_use`, add `DAY_USE`
  - multiply final total by `1.02`

### Formula

For a one-way distance-based trip:

`Estimated Price = Distance * SlabRate * 1.02`

For a round trip:

`Estimated Price = (Distance * SlabRate * 2) * 1.02`

For day-use:

`Estimated Price = (Distance * SlabRate + DAY_USE) * 1.02`

### Academic interpretation

This is a **piecewise tariff function**. The system does not use progressive billing per segment. Instead, it chooses one slab based on total distance and applies one rate to the entire route.

## 13.6 Cross-car comparison algorithm

Used in `getComparableCars()` and `renderCarOptions()`.

Logic:

- Recompute the same trip estimate for every comparable car.
- Separate cars into:
  - `withPrice`
  - `withoutPrice`
- Sort priced cars in ascending order by estimated cost.
- Render badges such as:
  - current car
  - cheapest now
  - cheaper by X

### Complexity

- Price estimation across `n` cars is O(n).
- Sorting comparable cars is O(n log n).

### Academic interpretation

This is a simple but useful **decision-support ranking algorithm** that transforms tariff data into user-facing comparative intelligence.

## 13.7 Booking overlap detection algorithm

Used in `create_car_payment`.

Logic:

- Define:
  - `booking_start = go_date`
  - `booking_end = return_date or go_date`

- Query existing bookings for the same car where status is `pending` or `confirmed`.
- Check whether stored booking intervals overlap with the requested interval.

### Academic interpretation

This is an interval-overlap detection rule at the database query layer. It prevents double-booking at the date level.

### Limitation

The conflict logic is date-based, not time-slot-based. Two bookings on the same day but at different hours are not treated as independent resources.

## 13.8 Mobile bottom-sheet snapping algorithm

Used in `getNearestSheetState(offset)`.

Logic:

- Measure the distance between the current drag offset and each allowed sheet state.
- Select the minimum-distance state.

This is a basic nearest-state snapping algorithm for touch UI behavior.

## 14. Payment Workflow Analysis

## 14.1 Input payload

The browser sends a JSON payload containing:

- customer name
- phone number
- trip type
- dates and times
- payment percentage
- total price
- distance
- origin text
- destination text
- car ID

## 14.2 Booking creation

The backend creates a `CarBooking` with:

- `status = pending`
- `payment_percentage = 50 or 100`
- `paid_amount = total * percentage / 100`

## 14.3 Kashier order generation

The system generates:

- `merchant_order_id = "car-" + booking.id`
- a signed hash using HMAC-SHA256
- a redirect URL to Kashier

The booking is therefore created before payment completion, and its state becomes authoritative only after the payment-return step.

## 14.4 Success processing

On a successful return:

- booking status becomes `confirmed`
- customer receives a WhatsApp confirmation
- driver receives a WhatsApp notification with:
  - customer details
  - trip type
  - dates
  - route text
  - Google Maps link based on textual locations
  - financial summary

## 15. Admin-Side Support

The Django admin provides administrative management for:

- `Car`
- `CarBooking`

### Car admin

Capabilities:

- list display
- filtering by brand, model, and availability
- search
- inline image management

### Car booking admin

Capabilities:

- list display for customer, car, date, status, price, and route
- search by customer and car metadata
- direct status editing
- bulk actions:
  - mark as confirmed
  - mark as cancelled

This is useful operationally because the booking lifecycle can be monitored without writing custom dashboards.

## 16. Legacy and Transitional Code Inside the Car Module

A very important academic observation is that the car subsystem contains both:

- current active code
- older legacy code that still exists in the repository

Examples include:

- `car_booking.html`
- `map_selection.html`
- `booking_success(request)` session-based legacy flow
- `Anaconda_bus_APP/static/js/main.js` with older Google Maps logic

This means the subsystem evolved over time and was partially refactored from a simpler Google-based version into a richer open-maps, AJAX-driven workflow.

## 17. Important Technical Inconsistencies and Risks

This section is especially important for a graduation-project discussion because it shows critical evaluation rather than only description.

## 17.1 Frontend price is trusted by the backend

The current endpoint `create_car_payment` accepts `total_price` from the browser and does not recompute it server-side from authoritative tariff fields.

### Why this matters

A malicious user can manipulate the JavaScript payload and send an artificially lower price.

### Academic conclusion

This is a **business-logic trust boundary problem**. The server should be the final authority for pricing.

## 17.2 Payment success endpoint does not verify callback authenticity

`car_payment_success` reads:

- `paymentStatus`
- `merchantOrderId`

from the query string and confirms the booking when the status equals `SUCCESS`.

### Why this matters

There is no visible server-side verification of:

- Kashier signature
- webhook authenticity
- payment confirmation from Kashier servers

### Academic conclusion

This is a **payment confirmation integrity risk**.

## 17.3 The model contains outdated pricing logic

`CarBooking.calculate_total_price()` refers to:

- `price_per_km_below_300`
- `price_per_km_above_300`

These fields do not exist in the current `Car` model, which now uses detailed slab fields such as `price_per_km_0_100` and `price_per_km_101_200`.

### Academic conclusion

The repository contains **schema/business-rule drift** between model methods and the active frontend pricing engine.

## 17.4 Duplicate `total_price` declaration in `CarBooking`

Inside the class body, `total_price` appears more than once. In practice, the later declaration overrides the earlier one at Python class-definition time.

### Academic conclusion

This does not necessarily break runtime behavior, but it is a maintainability issue and indicates code duplication.

## 17.5 Legacy booking flow is broken or stale

The legacy `booking_success(request)` flow uses field names inconsistent with the current model:

- it expects `booking_data['name']`
- the form actually uses `customer_name`
- it tries to instantiate `CarBooking(name=...)`, while the model field is `customer_name`

### Academic conclusion

The repository contains a **retained obsolete path** that should not be presented as the active production flow.

## 17.6 `car_list.html` references fields not present in the current model

The list page references:

- `car.price_per_KM`
- `car.fuel_type`

These are not current `Car` fields.

### Effect

The template may render incomplete or empty values.

### Academic conclusion

This is another case of **view-model mismatch**.

## 17.7 `Car.clean()` overlap validation only applies on update

The overlap check in `CarBooking.clean()` is conditioned on `self.pk`, which means it is effectively applied only when the object already exists.

### Effect

Creation-time protection depends mainly on `create_car_payment`, not on the model itself.

### Academic conclusion

This weakens domain integrity because the model is not fully self-protective.

## 17.8 Date validation inconsistency

`create_car_payment` allows:

- `return_date == go_date`

because it only rejects cases where return date is strictly less than go date.

However, `CarBooking.clean()` rejects:

- `go_date >= return_date`

which means same-day round-trip behavior is inconsistent between layers.

### Academic conclusion

This is a **validation inconsistency between controller and model layers**.

## 17.9 Availability flag is not enforced at catalog level

`car_list` uses all cars when no filter is applied and does not restrict the query to `is_available=True`.

### Effect

Unavailable cars may still appear in the public catalog.

## 17.10 WhatsApp instance ID is hardcoded

The WhatsApp helper uses a hardcoded `INSTANCE_ID` instead of consistently using the environment variable already declared in settings.

### Academic conclusion

This reduces deployment flexibility and increases configuration coupling.

## 17.11 No automated tests for the car module

The app test file is effectively empty with respect to the car workflow.

### Academic conclusion

The subsystem currently lacks regression protection in:

- pricing rules
- overlap detection
- payment flow
- map endpoint behavior

## 18. Strengths of the Current Design

Despite the above issues, the module has several strong engineering qualities.

- It has a clear end-user flow from discovery to checkout.
- It uses open mapping infrastructure rather than hard dependency on a commercial provider.
- It implements graceful fallback in the map backend.
- It offers rich route interaction and mobile-friendly UI behavior.
- It supports both fixed-price and distance-based services.
- It includes a useful comparison engine across vehicles.
- It stores bookings before payment completion, which is operationally practical.
- It integrates customer and driver notifications automatically.

## 19. Recommended Improvements for a Graduation-Project Version

If this subsystem is to be presented academically, the following improvements should be proposed clearly.

- Recompute all prices on the server side and ignore client-supplied totals except as advisory values.
- Verify Kashier callbacks using a secure server-to-server or signed verification flow.
- Refactor `CarBooking.calculate_total_price()` to match the actual slab structure.
- Remove or archive broken legacy flows.
- Normalize template field usage with the current model schema.
- Enforce `is_available=True` in public catalog queries unless intentionally overridden.
- Move pricing logic into a dedicated pricing service class.
- Move map adapter logic into a dedicated service module.
- Add test coverage for:
  - tariff calculation
  - overlap detection
  - route API fallbacks
  - payment status transitions
- Consider time-slot-based conflict detection if same-day multiple bookings must be supported.

## 20. Suggested Academic Chapter Structure for Submission

If you want to convert this directly into a graduation-project document, the `/cars` chapter can be organized like this:

1. Introduction to the car rental subsystem
2. Functional requirements
3. Non-functional requirements
4. System architecture
5. Database design
6. User interface design
7. Map integration design
8. Pricing algorithm
9. Booking conflict detection
10. Payment gateway integration
11. Notification workflow
12. Security considerations
13. Testing strategy
14. Limitations and future work

## 21. Proposed Formal Conclusion

The `/cars` module in the Allen Bus Management project is a meaningful applied software subsystem that combines catalog management, geographic interaction, route computation, dynamic pricing, booking persistence, payment integration, and operational messaging into one workflow. Technically, it demonstrates full-stack integration across Django, JavaScript, mapping engines, and payment infrastructure. From an academic standpoint, its strongest value lies in the way it connects several applied software engineering domains inside a single user journey.

At the same time, the current implementation also shows realistic software evolution patterns: legacy code retention, controller-model inconsistency, client-side business-logic exposure, and incomplete verification in sensitive payment flows. These points should not be hidden in an academic presentation. On the contrary, they strengthen the technical discussion because they show that the project can be critically analyzed, not merely described.

For graduation-project use, this subsystem is suitable as a case study in applied web engineering, transport-service digitization, map-driven booking systems, and mixed business-rule orchestration between frontend and backend layers.
