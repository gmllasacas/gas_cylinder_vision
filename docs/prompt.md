I want to build a web application:

- to count my daily movement of domestic gas cylinder of 10kg (aka product) inside my warehouse (in an out)
- for this I have a camera IP, so this application should read that camera stream and analyze it to look for the product
- from left to right should be IN
- from right to left should be OUT
- the counter should be by the day
- for development purposes we should use a saved MP4 video instead of the stream

Users:

- administrators only

Main workflow:

- the admin log in the application
- this admin should be able to see the live feed analysis of the application when counting the gas cylinders
- this admin should be able to see the history of the counting by the day

Constraints:

- Technology: open for any tech stack, but this application should be able to run on a shared webserver if possible
- budget: start with a budget friendly application for 1 user
- deadline: to be developed by 1 person
- compatibility: to be used in chrome
- security: only admin access to the application, assume that the feed is a IP Camera and the server is going to have access to that

Act as the planning model. Do not implement changes yet.

1. Identify ambiguities that materially affect the product or architecture.
2. Ask me the minimum necessary questions, like:
   - architecture
   - tech stack
3. After I answer, produce a Project Execution Contract containing:
   - objective;
   - current state;
   - included and excluded scope;
   - numbered requirements;
   - interfaces and data contracts;
   - constraints;
   - acceptance criteria;
   - exact verification procedures;
   - execution plan;
   - approval boundaries;
   - assumptions and risks;
   - definition of done.

Requirements must describe observable behavior. Every requirement must
have at least one testable acceptance criterion. Mark the contract
“Proposed”; do not begin implementation.


Deployment architecture: this is a R&D project
- phase 1: for the time being is going to be on a local machine inside the warehouse
- phase 2: to push the application to a webserver
Technology: I think all Python is the way 
Camera access: 
- phase 1: the IP camera is going to be on the same network of the machine
- phase 2: manage of admins
Counting behavior: 
Detection scope: 
Audit/history: 
Development input and target: 
- phase 1: use the MP4 video file inside the resource folder
- phase 2: 
Authentication:
- phase 1: only 1 admin
- phase 2: management of admin users

Material ambiguities:
Deployment architecture: Computer-vision processing requires a persistent process, which most shared PHP hosting does not support. Can we use a low-cost VPS or a local warehouse computer for detection, with the web dashboard hosted separately if needed?
Technology: Is a PHP web application plus a Python/OpenCV detection worker acceptable? This is the recommended budget-friendly stack.
Camera access: Will the production camera provide RTSP, and can the processing machine access it over the warehouse network? Please provide the expected resolution/FPS if known.
Counting behavior: Should a cylinder count only after its center crosses a configured virtual line? How should partially visible, stationary, overlapping, or reversed-before-completing-crossing cylinders behave?
Detection scope: Must the system distinguish 10 kg cylinders from other cylinders/objects, or will every cylinder-shaped product in the counting zone be a 10 kg cylinder?
Audit/history: Should each count store only date, direction, and timestamp, or also an evidence image/video clip? Are manual corrections and CSV export required?
Development input and target: Is the saved MP4 already available in this workspace? What accuracy target, processing speed, and delivery deadline should acceptance testing use?
Authentication: Is one fixed administrator account sufficient initially, or must administrators be manageable through the application?