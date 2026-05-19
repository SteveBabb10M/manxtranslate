<?php
/**
 * Manx Translator API Proxy (Enriched v2)
 * Holds the Anthropic API key server-side.
 * Accepts translation requests from the front end, forwards to Claude.
 *
 * Deploy to: /var/www/html/manx-translate-api.php
 * 
 * v2 changes:
 * - CORS updated for historicallymanx.com
 * - System prompt enriched with 578 Coonceil ny Gaelgey vocabulary entries
 * - Grammar rules (lenition, eclipsis, word order, copula) injected
 * - Source: kscanne/gaelg + CnyG official terminology
 */

// CORS - allow requests from both domains during transition
$allowed_origins = [
    'https://historicallymanx.com',
    'https://www.historicallymanx.com',
    'https://revestment1765.com',
    'https://www.revestment1765.com'
];

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (in_array($origin, $allowed_origins)) {
    header("Access-Control-Allow-Origin: $origin");
} else {
    header("Access-Control-Allow-Origin: https://historicallymanx.com");
}

header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json; charset=utf-8");

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// --- CONFIGURATION ---
$ANTHROPIC_API_KEY = getenv('ANTHROPIC_API_KEY') ?: 'YOUR_API_KEY_HERE';

// Rate limiting: max 20 requests per hour per IP
$rate_limit_dir = '/tmp/manx_translate_ratelimit';
if (!is_dir($rate_limit_dir)) {
    mkdir($rate_limit_dir, 0755, true);
}

$client_ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$rate_file = $rate_limit_dir . '/' . md5($client_ip) . '.json';
$rate_window = 3600; // 1 hour
$rate_max = 20;

$now = time();
$requests = [];
if (file_exists($rate_file)) {
    $requests = json_decode(file_get_contents($rate_file), true) ?: [];
    $requests = array_filter($requests, function($t) use ($now, $rate_window) {
        return ($now - $t) < $rate_window;
    });
}

if (count($requests) >= $rate_max) {
    http_response_code(429);
    echo json_encode(['error' => 'Rate limit exceeded. Please try again later.']);
    exit;
}

$requests[] = $now;
file_put_contents($rate_file, json_encode(array_values($requests)));

// --- PARSE REQUEST ---
$input = json_decode(file_get_contents('php://input'), true);
if (!$input || empty($input['text'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing text field']);
    exit;
}

$text = trim($input['text']);
$direction = ($input['direction'] ?? 'en-gv') === 'gv-en' ? 'gv-en' : 'en-gv';

if (mb_strlen($text) > 2000) {
    http_response_code(400);
    echo json_encode(['error' => 'Text too long. Maximum 2000 characters.']);
    exit;
}

// --- EXAMPLE TRANSLATIONS ---
$examples = <<<'EXAMPLES'
English: The Duchess! Oh my dear paws! Oh my fur and whiskers! She'll get me executed, as sure as ferrets are ferrets!
Manx: Y Vendiuic! Ogh my vaaigyn veen! Ogh y fynney as ny robaigyn aym! Bee'm currit gy baase eck, cho shickyr as dy vel ferradyn nyn verradyn!

English: "I thought it would," said the Cat, and vanished again.
Manx: "Heill mee dy jinnagh," dooyrt y Kayt, as skell eh roish reesht.

English: Their armour was a major hindrance to them.
Manx: Ny eillaghyn va daue mooarane cumrail.

English: Poorly enough, I'm thinking, but she has a good heart.
Manx: Moal dy liooar, er-lhiams, agh ta cree vie eek.

English: Good luck to thee and prosperity in the new country.
Manx: Aigh vie ort, as sonnys ort 'sy cheer noa!

English: He was complaining about everything.
Manx: V'eh gaccan mysh dy chooilley nhee.

English: I say that it's a fine sunny day.
Manx: Ta mee gra dy vel laa braew grianagh ayn.

English: Aw, am not, am not, I am not for walking now at all.
Manx: Aw, cha nel, cha nel, cha nel mee son shooyl nish edyr.

English: people need young folk now to set potatoes.
Manx: ta sleih laccal feallagh aegey nish dy soie praaseyn,

English: The society seems to me to be completely dead, the blaming not lying on one man or woman alone, but upon us all.
Manx: Ta'n cheshaght jeeaghyn dooys dy ve slane marroo, cha nel y foill ny lhie er 'un dooinney ny ven ny lomarcan, agh orrin ooilley.

English: There was not a word of apology; they cared nothing for the anguish they caused my mother.
Manx: Cha row fockle erbee dy leshtal oc; by gummey lhieu yn angaaish va currit er my voir.

English: Let me tell you how it came about that I was born in Liverpool.
Manx: Lhig dou ginsh diu kys haink eh gy kione dy row mee ruggit ayns Liverpool;

English: I haven't noticed anything yet. Maybe that was another promise that has been broken.
Manx: Cha nel mee er n'ghoaill tastey foast jeh veg. Foddee dy row shen gial elley ta er ve er ny vrishey.

English: Also, an account of the first king there was of Mann, and his line; an account of the Lords, and how the Island came to the Stanley clan.
Manx: Myrgeddin coontey jeh'n chied Ree va Mannin, as e Lhuight; coontey jeh ny Chiarnyn, as kys haink yn Ellan gys Clein Stanley.

English: The young woman ran home greatly afraid and she arrived at the house out of breath and shaking all over.
Manx: Roie y ven aeg dy valley as aggle mooar urree as rosh ee yn thie eck ass ennal as ooilley er creau.

English: When I was writing the column last week, it was before the Chieftans had come to our Island.
Manx: Tra screeu mee yn colloo yn shiaghtin shoh chaie, v'eh roish my row ny Flahee (the Chieftans) er jeet gys nyn ellan.

English: Let us seriously consider this, and pray God to fit us for the Hour of death.
Manx: Lig dooin shoh y ghoaill gys nyn gree, as guee er Jee shin y yannoo aarloo son oor y vaaish.
EXAMPLES;

// --- COONCEIL NY GAELGEY VOCABULARY (578 entries) ---
// Source: Official Manx terminology from Coonceil ny Gaelgey (focCnyG5, CnyG3, computer terms)
$vocabulary = <<<'VOCAB'
academic = acadeamagh
access = cair f -entreil
access list = list m –entreilys
accession = entreilys m
accreditation = credjoonaght f
acupuncture = lheihys m -doral
acute health services = shirveishyn fpl
added value = feeuid f currit rish
addictive = neu-lhiggagh
administration of justice = shirveish f
adrenaline = adrenaleen m
advanced search = shirrey m myn
aftercare = eear-chiarail f
aftershave lotion - = loish f lurg-
alcoholic liquor = liggar m
allergic = allergagh
almond-leaved willow = shellagh f almonagh
amendments, make = jean
ancient history = shennaghys m y
animal health = slaynt f beiyn
animate* = bioghee, bioghey
animated adj, pp = bioghit
animated gifs npl = jallooyn m
animation* = annymaght f; bioghys
anti-microbial = noi-vynvioaghagh
antimony = antimoan m
appendicectomy = goaill magh
apply* = cur rish, cur rish
architecture = seyrnaght f
archive = tashtlann m
argon = argon m
aroma therapy = lheihys m -soar
arrestable offences = loghtyn mpl fo
arsenic = arsnick
arthritis = oltys m
as an attachment = myr lhiantag
asparagus tips = baareyn mpl lus ny
assessment base = undin m son
assessment of performance = sessal m
Assessor of Income Tax, the = Ard-
assets, charging of = cur cooid fo
astatine = astatçheen m
atonal = neuhoanoil
atonality = neuhoanoilaght f
attachment* = lhiantag f
attorney, powers of = pooaraghyn mpl
audio file* = coadan m –sheean
authoring language = glare f -screeuee
backup = jeenane m
balancing payment = eeckys m
birch bracket fungus = fungys m
bird cherry tree = billey m shillish
bismuth = bismut m
block of flats = block m dy
blog = blog m
books, collection of = lioarlagh m
boron = boron m
bowel cancer = kahngyr m -minnagh
breast of chicken = cleeau f chirkey
breast screening = scannal m -keeagh
broadband = bann m lhean
bromine = bromeen m
browser = jeeagheyder m
bug = freetçh f scaapagh
cable* = caabyl m
cache = freill, freayll
caecal = kaikoil
caesium/cesium = kaishum m
cancel* = scryss, scryssey
canned beans = poanraghyn mpl
canned fish = eeast m stainnit
canned meat = feill f stainnit
canned soup = awree m stainnit
capital equipment = cullee f veayn
car sharing = rheynn f carryn
carbon = carboan m
carbon dioxide = daa-ocseed f
cardiac = cardiagh
cardiothoracic = creetoracksagh
care pathway, the = cassan m y
cat food = bee m -kayt
cat litter = stoo m -premmee kayt
cerobrovascular = kerrochuishlagh
cesium/caesium = kaishum m
chat* = cowag f
chief executive officer = ard-offishear
child custody = cair f -freayll paitçhyn
chip = slissag f
chlorine = cloreen m
chocolate mint = shocklaid f -
cholecystectomy = kolakystectomys m
chronically sick = sheer çhing
civil = theayagh
civil aviation = etlagh m sheeoil
civil jurisdiction = briwnys m neu-chimmagh
civil liability = currym m
civil penalties = kerraghyn mpl
click here = crig ayns shoh
click on = crig er
click to enlarge = crig as mooadee
click* = crig, criggaragh
climate = emshyraght f
climate change = caghlaa m
cling film = fillym m lhiantagh
clinical pathways = raaidyn mpl -lhee
close the case = cur kione er y
closed circuit television = çhellveeish
cobalt = cobalt m
collapse (windows) = lhieg, lhieggey
collection of books = lioarlagh m
collective = co-chadjin
comment* = baght m
commercial dealing = dellal m son
commitment = barrantys m
computer lab = shamyr f cho-earrooder
computer suite = co-hamyryn f
computer* = co-earrooder m
confectionery = miljanyn mpl
confiscation = glackey m
conformity = coviallys m
congenital = eiraghtoil
conifer plantation = keyll f ny biljyn-
connected purposes = cooishyn fpl
consequential provisions = conaantyn
conservation = freayltys m
console = boayrd m –reill
consumable = ry cheau
consumers = feallagh mpl -kionnee
contact us = cur fys orrin
contact* = cur fys er, cur fys er
content = stoo m -sthie
contractual obligations = currymyn
control of employment = gurneil m - failley
control* = niart m -stiuree (er)
conveyancing = livrey-ys m thalloo
cooid onneragh gyn kied = pirate goods
cooked meat = feill f choagyrit
cookie = minniag f
copper = cobbyr m
copper pair = piyr f dy trengyn-cobbyr
copy* = coip m
cordless adj = gyn streng
core services = shirveishyn fpl -cree
coroner of inquests = toshiagh m -
corporate = co-chorpagh
cosmetics = cooid f chosmaidagh
cough mixture = medshin m scoarnee
crab apple tree = billey m ooyl feie
creeping willow = shellagh f hallooin
criminal = kimmeeagh
criminal justice = cairys m kimmee
criminal proceedings = cooishyn fpl -
crisps = crispyn mpl
cross-matched = tessen-soylit
cross-matching = tessen-soylaghey m
cruelty to animals = dewilys m noi
cultural sovereignty = seyrsnys m
cummalagh = inclusive
cur ass, cur ass = repeal
currency (money) = argid m cadjin
cursor = quaillag f
custody = freayll fo ghlass
customer information = fysseree m da
customer information centre = laare
cut* = giar, giarrey
cycling = roarey m
cytocytoxic = killag-nieuagh
dark bush cricket = criggad m y
data = fysseree mpl
database manager = reireyder m stoyr-fysseree
day-release training = traenal m kied
decagon = jeihin m
deconsecration = neuchasherickey m
defamation = luney m
demolition = lhieggey m
dentistry = feeackleyraght f
deputy headteacher = lhiass-
dessert sundries = miljagyn fpl
desserts = miljagyn fpl
Diocese of Sodor and Man = Aspickys m
disabled toilets = premmeeyn fpl ny h-
dish of the day = bee m yn laa
documentary = claare m feer-
dodecagon = daa-yeigin m
dog food = bee m -moddee
dooin magh, dooney magh = exclude
double cream = key m glubbagh
downloads = jeelaadyn mpl
dramatic works = drammaghyn mpl
drug trafficking = dellal m ayns
duck paté = teayst f -thunnag
ecclesiastical = agglishagh
economic trend = beoyn m yn arrys-
education = ynsagh m
educational exchange = maylartey m
effectiveness = breeoilid f
eiraghtoil = congenital
emergency death = baase m gear-
endoscopy = endoscopys m
endurance-racing = ratçhal m -
energy drinks = joughyn fpl bree
entertaining = eunysseyragh
environment = çhymmyltaght f
equivalent number = earroo m
er aght oardit = prescribed
estates of deceased persons = cooid
ethnic origin = bunneydys m
evolution = evloid f
excellence = erbaghtallys m
exciting - = greesoil
executive support officer = oikagh m
exhibition centre = ynnyd m
expenses = baarailyn fpl
facial tissues = pabyryn mpl-bog eddin
family income supplement = bishagh
family law = leigh f yn lught-thie
first aid station = ynnyd m kied
fixed line services = shirveishyn fpl
fizzy drinks = joughyn fpl breeoil
fluorine = fluoreen m
folklore = beeal-arrish f
food wrap = filtag f vee
foodstuffs = stoo mpl -beaghee
foreign currency = argid m joarree
forestry = keylljyn fpl
fortified wine = feeyn m niartit
full board = lane-veaghey m
funding application = shirrey m -
furniture = trosgan m
gaming = kiarrooghys m
gammon = gamboon m
General Gaol Delivery, Court of = Quaiyl f
generating station = ynnyd f -gientyn
geo-energy = bree m -thallooin
geothermal energy = bree m chiass-
geriatric people = y feer-henndiaght f
glack, glackey = confiscate
glackey = confiscation m
global warming = çhiow m ny
gold = airh f
gorse scrub = reeast m aittin
Governor in Council = yn Kiannoort m ayns
graphic novel = oorskeeal m
grey sallow = shellagh f lheeah
guardianship = oaseiryn mpl -clienney
haematology = fuill-oaylleeaght f
half board = lieh-veaghey m
harbourside = çheu f yn phurt
health outcomes = troaryn mpl -slaynt
hendecagon = un-jeigin m
heptagon = shiaghtin m
hexagon = sheyin m
High Court = Ard-whaiyl f
high dependence beds = lhiabbaghyn
histopathology = histopatoaylleeaght f
hoghtad = eighty
household cleaner = glenneyder m
human tissue = stoo m kirp gheiney
hurdling = cleeaderys m
hydrogen = hiddragien m
hypnotism = saveenaghey m
imaging = n jallooaghey m
imperfect tense = emshir f -chaie
improvement = shareaghey m
incapacity = annoonid f
inclusive = cummalagh
incorporation = cochorpaghey m
independent financial adviser = coyrlagh m
information = fysseree m
infrastructure = bun-troggalys m
initiation ceremony = jesh-chliaghtey
insensitive = neuennaghtagh
insider trading = dellal m çheu-sthie
installations, offshore = cullee fpl sy
interception = brishey m -stiagh
internet services = shirveishyn fpl
internment = pryssooney m ny
internment camp = camp m ny
intoxicating = meshtoil
iodine = eeadeen m
iron = yiarn m
jean femblal, femblal = edit
jean freeghey, freeghey = fry
junior (concerned with age) = poinnaragh
kiarad = forty
kiare, kiarail = supply
kimmeeagh = criminal
kitchen roll = rollaghyn mpl shamyr-
krypton = krypton m
lane Gaelgagh = Manx medium
large-leaved lime tree = theiley duillag vooar
lead = leoaie f
leading firefighter = moogheyder m
legal aid = cooney m leighoil
legal separation = scarrey m leighoil
legitimacy (of child) = lowallys m -clienney
liability, civil = currym m neu-
Lieutenant-governor = Lhiass-
Limitation Act = Slattys m Caglieeyn Leighoil
limited (company) = çhiarmaanit
loaght, loaghtey = process
long life fruit juice = soo m mess
long life milk = bainney m beayn
long-term = foddey-çharrymagh
long-term condition = stayd m
maintenance payments = argid m -
malfunction = meeobbraghey m
Management = Undinys Oaseirys as
manganese = manganaish f
Manx coastal waters = ushtaghyn mpl
Manx folklore = beeal-arrish f Vannin
Manx medium = lane Gaelgagh
marine aquaculture = eirinys m -marrey
marine biodiversity = bea-neuchaslys
marine nature reserve = kemmyrk f
maritime security = sauçhys m -marrey
married parties/couples = sheshaghyn mpl -poost
Mayfly larva = crooag f y whaillag
Medical Acts = Slattyssyn mpl ny Fir-
medical assessment unit = unnid f
medieval history = shennaghys m ny
melon cocktail = jinlag f -melloon lesh mess
mental health = slaynt f inçhynagh
merchant shipping = lhuingys m -dellal
mercury = mercur m
meshtoil = intoxicating
mesolithic age, the = yn eash f chloaie
microwave oven = oghe f meegra-
mineral water = ushtey m meainagh
mineral workings = obbraghyn mpl -
minerals = stoo mpl meainagh
minimum wage = faill m sloo
minors = sleih mpl fo eash
mission statement = fockley m -dean
modern history = shennaghys m
molybdenum = molybdenum m
money laundering = nieeaghyn m -
multidisciplinary = yl-cheirdagh
myn-vrish, myn-vrishey = analyse
neon = neoin m
neonatal = noa-ruggit
neonatal clinic = lheelann m da
network services = shirveishyn fpl -
neu-lhiggagh = addictive
neu-lowal = unauthorised
neurology = neayroaylleeaght f
neurosurgery = neayrlauelheeys m
nickel = nickyl m
nitrogen = neetragien m
noi = relax restrictions on
non-corporate = neu-chorpagh
non-emergency death = baase m gyn
non-resident = mooie
nonagon = nuyin m
notary public = scrudeyr m oikoil
nursery = oikanagh
nutritional therapy = lheihys m -
nuyad = ninety
obsolete provisions = shenn-reillyn
obstetrics = ruggyr-oaylleeaght f
occupancy of beds = ymmyd m
octagon = hoghtin m
offshore installations = cullee f sy
oikanagh = nursery
oncology = aasoaylleeaght f
open (as ground) = lhome
operations director = stiureyder m
ophthalmology = sooill-oaylleeaght f
oral surgery = laue-lheeys m -beill
orange ladybird = deyllag f vreck
organ transplants = aa-hoiaghey mpl
orthopaedic = ortopeedagh
orthopaedics = ortopeedaght f
oxygen = ocsygien m
paediatric = peediatragh
paper clip = greimmeyder m --pabyr pl
paracetamol = paracaitamol
past tense = emshir f -chaie
pasta = pastey m
pasta sauces = aunlynyn mpl pastey
pastries = paistreeyn mpl
pate = pâté m
penalty, death = kerraghey m -baaish
pentagon = queigin m
perfect tense = emshir f -chooilleenit
performance indicators = cowraghyn
personal allowance credit = daill f
personal use = ymmyd m persoonagh
personnel = skimmee m
pest control = smaghtaghey m noidyn
pet food = bee m -biggin
phonics = sheean m -lhaih
pine needles = jilg-juys fpl
pirate goods = arrish cooid onneragh
platinum = platinum m
playgroup = possan m -cloie
plum sauce = aunlyn m -plumbyssyn
pluperfect tense = emshir f roie-
poached salmon = braddan m scoaldit
pocket money = argid m poggaid
poinnaragh = junior
positive lifestyle = aght m -bea jarrooagh
postgraduate = eearcheimagh
poultry = feill f eean
powers of attorney = pooaraghyn mpl
pregnancy, terminate = moogh
prehistoric = ro-hennaghyssagh
prehistory = ro-hennaghys m
prescribed = er aght oardit
press release = cur-magh m naight
primary care = ard-chiarail f
Primitive Methodist = Saasilagh m
procedures = aghtyn mpl
proceedings = immeeaghtyn fpl
proceeds = cosnaghyn mpl
proceeds of crime = leagh m -
promontory fort = doon m kione-
promulgation = fockley m magh
property = cooid f -seihllt
property service charges = eeckyn
prostatectomy = prostatectomys m
public = foshlit
public entrance = entreilys m y
public health = slaynt f y theay
public opinion survey = creearey m
public order = ymmyrkey m -bea yn theay
public records = recortyssyn mpl y
public, the y = theay m
purple willow = shellagh f ghorrym
pussy/goat willow = shellagh f yial
pyramid selling = creck m pyramidoil
quality of life survey = creearey m
queigad = fifty
race relations = commeeys m eddyr
radiotherapy = scell-lheihys m
radon = raadon m
recall service = shirveish f geamagh
reciprocal = cagh y cheilley
reciprocal enforcement = eignaghey
recreation = ooraghey m
reference book = lioar f fysseree
reflexology = teaystey m coshey
registered club = sheshaght f
regulation = gurneil m
reill, reill = to be in charge of
relax restrictions on = eddrymee
relief = feaylsey m
rented properties = cummallyn mpl -
representation of the people = tuarystallys m y
research = ronsaghey m
resources = cooid f
respect = arrym m
resuscitation guidelines = linnaghyn
revestment = aa-ghreim m
road traffic = troailtys m -raaidjey
ronsee, ronsaghey = research
safety equipment = cullee f -hauçhys
salvage = sauail f -lhuingys
sanderling = leayrane m glass
satellite navigation = sat-stiureydys m
savoury biscuits = brishtagyn fpl neu-
school crossing patrol officer = fer m
school-age = eash f scoillaragh
science fiction film = fillym m far-
sea bindweed = lus f -chianglee ny
sea fisheries = eeastagh mpl -marrey
sea ivory = faasaag f ny greg
sea terminal building = troggal m
securities = screeunyn mpl raanagh
selection = of fresh vegetables reih m lossreeyn
selection of fresh vegetables = reih m
self esteem = hene-arrym m
semi-skimmed milk = bainney m
senior = shanstyragh
senior medical staff = ard-skimmee m
sewage = sornaigys m
sewage disposal works = obbraghyn
sexual offences = loghtyn mpl
sharing = co-ymmyd m
sheer çhing = chronically sick
shellfish = eeast m shliggagh
sheyad = sixty
shiaghtad = seventy
shop hours = ooryn fpl -foshlee
shower gel = gloagh m frass-oonlee
silicon = shillagon m
silver = argid m
single cream = key m keyl
single member company = sheshaght
sixth form college = colleish f sheyoo-
skimmed milk = bainney m scarrit
small-leaved elm = lhiouan m duillag veg
smooth-leaved elm = lhiouan m duillag rea
social media = meanyn mpl sheshoil
soft drinks = joughyn fpl neu-lajer
soprano recorder = feddan m millish
sorçh, sorçhal = grade
sparkling wine = feeyn m breeoil
speculative dealing = dellal m
sponsorship = gialdynys m
staff = skimmee m
staggered = straneagh
standard = cadjin
statute law = y leigh f scruit
statutory board = boayrd m
stored (data) = tashtit
stow er, stowal er = confer on
strawberry sauce = aunlyn m
substitute = ynnydeyragh
suite = co-hamyryn fpl
sulphur = sulfur m
summary jurisdiction = briwnys m
summary offences = loghtyn mpl hig
supermarket trolley = bastag f
supervision = oaseirys m
supervisory = supervisory
supervisory management = stiurey m
supply = livrey-ys m
surgical operations = obbraghyn mpl
Synod, General = Ard-choyrle f Chadjin
tantalum = tantalum m
tax avoidance = shaghnys m
telecommunications = çhellinshagh
temporary = tammyltagh
tenor recorder = feddan m millish
terminate pregnancy = cur jerrey er
terms = conaantyn mpl
terms of reference = cagleeyn mpl -
terrorism = tranlaase f -agglee
the y = ving f cour druggaghyn as
thorax = toraks m
timeshare = cronney m -imbee
tinder fungus = fungys m y sponk
tobacco products = troaryn fpl
toilet cleaner = glenneyder m
tonal = toanoil
tort (legal) = aggairyn nfpl
training department = rheynn f
transfer of care = livrey m kiarail
treead = thirty
treisht da, treishteil da = vest in
tridecagon = tree-jeigin m
trog veih, troggal veih (argid) = charge
tungsten = tungsten m
ultrasound = feer-heean m
unauthorised = neulowal
undertaking(s), gas = dellal m gas
updating = jeianaghey m
urology = ooroaylleeaght f
vandalism = milley m
varrey as y = cheesh f sthie
vehicle duty = keesh f charbyd
velvet swimming crab = partan-
Viking influence = bree m ny
Villa Marina = Plaase f ny Marrey
visual arts = ellynyn fpl sooilley
volleyball = bluckan m -etlee
weights and measures = trimmidyn
welfare = lhiass m
well-being = gien m mie
whole milk = bainney m neuscarrit
wild cherrey tree = billey m shillish
wild cherry tree = billey m shillish feie
wildlife = cretooryn mpl feie
woodland hawthorn = drine m -
word processing = obbraghey m
wych elm = lhiouan m
xenon = xenon m
ynnydeyragh = substitute
yoghurt = binjean m
yoghurt, black cherry = binjean m
yoghurt, fruity = binjean m lesh mess
yoghurt, low fat = binjean m beggan
yoghurt, peach melba = binjean m
yoghurt, strawberry = binjean m
zinc = shinc m
çhellinshagh = telecommunications
“at” sign (@) = feoghaig
VOCAB;

// --- MANX GRAMMAR RULES ---
$grammar = <<<'GRAMMAR'
• Comparative: ny + s-form or analytical ny smoo + adj (*ny stroshey* (stronger), *ny smoo taitnyssagh* (more pleasant))
• Adjective lenited after feminine singular noun (*ben vie* (good woman, < mie), *blein vooar* (great year, < mooar))
• Adjectives follow the noun (*thie beg* (small house), *moddey mooar* (big dog))
• Superlative: y/yn + s-form (*yn stroshey* (the strongest))
• cha nee (is not) (*Cha nee Manninagh mee* (I am not Manx))
• by/ba (was) + lenition (*By vie lhiam shen* (I liked that, lit. was good with-me that))
• she (is) - identifies, classifies, emphasises; often in cleft constructions (*She Manninagh mee* (I am Manx), *She dooinney mie eh* (He is a good man))
• nee (is it?) in questions (*Nee Manninagh oo?* (Are you Manx?))
• she classifies/identifies ('is a'), ta describes state/location ('is being/is at') (*She fer-Loss eh* (He is a gardener) vs *T'eh gobbragh* (He is working))
• After plural definite article ny (*ny girree* (the cocks, < kirree - but eclipsis rare in modern Manx))
• After possessive nyn (our/your pl./their) (*nyn gione* (our head, < kione), *nyn dhie* (our house, < thie))
• After preposition ayns yn (in the) (*ayns yn gharey* (in the garden, < garey))
• After definite article yn + feminine singular noun (*yn vlein* (the year, < blein), *yn chabbane* (the cabin, < cabbane))
• After daa (two) (*daa vlein* (two years, < blein), *daa hie* (two houses, < thie))
• After possessive adjectives my (my), dty (your sg.), e (his) (*my vlein* (my year), *dty hie* (your house), *e charrey* (his friend))
• After prepositions: er (on), fo (under), ny (than), ro (too), dy (to/particle) (*er vullagh* (on top, < mullagh), *fo halloo* (underground, < thalloo))
• After verbal particles dy/nagh in dependent clauses (*dy voddin* (that I might, < foddin), *nagh vel* (that is not, < vel))
• Past tense of regular verbs (*hug* (gave, < tug/cur), *hilg* (threw, < tilg))
• After particles cha (not) and nagh (that...not) (*cha vel* (is not), *cha jarg* (cannot, < jarg))
• After vocative particle y/a (*y harvaant* (O servant, < sharvaant))
• Adjective lenited after feminine singular noun (*ben vie* (good woman, < mie), *blein vooar* (great year, < mooar))
• yn (the) before singular; ny before plural. No indefinite article (*yn dooinney* (the man), *ny deiney* (the men), *dooinney* (a man))
• Two genders: masculine and feminine. Gender affects article, lenition of adjectives, and pronoun agreement (*yn dooinney mooar* (the big man, no lenition), *yn ven vooar* (the big woman, lenition))
• Genitive formed by juxtaposition: possessed + possessor (*dorrys y thie* (door of the house), *bainney ny baa* (milk of the cow))
• 7 plural classes: -yn (regular), -aghyn, -yn with vowel change, -eeyn, -tyn, vowel change only, irregular (*thieyn* (houses), *cabbil* (horses < cabbyl), *kirree* (sheep < keyrrey))
• Counting form (no noun): nane, jees, tree, kiare, queig, shey, shiaght, hoght, nuy, jeih (Traditional: *nane-jeig* (11), *daa-yeig* (12), *tree-jeig* (13)...)
• daa (two) + singular noun + lenition (*daa vlein* (two years), *daa hie* (two houses))
• Manx traditionally uses vigesimal (base-20) counting; decimal also used in modern Manx (Vigesimal: *feed* (20), *daeed* (40 = 2x20), *tree feed* (60 = 3x20))
• tree (3) to jeih (10) + plural noun (*tree thieyn* (three houses), *queig bleeantyn* (five years))
• un (one) + singular noun + lenition (*un vlein* (one year, < blein))
• Common compound prepositions: er-ash (back), er-lheh (separate), mysh (about), trooid (through) (*Haink eh er-ash* (He came back), *mysh tree bleeaney* (about three years))
• Prepositions inflect for person/number (prepositional pronouns) (*ec* -> aym, ayd, echey, eck, ain, eu, oc)
• Many prepositions trigger lenition: er (on), fo (under), dy (to), ny (than), ro (too), veih (from) (*er vullagh* (on top), *fo halloo* (underground), *dy vie* (well, lit. to good))
• shoh (this), shen (that), shid (yonder); used after noun (*yn dooinney shoh* (this man), *yn lioar shen* (that book), *yn thie shid* (yonder house))
• Independent: mee (I), oo (you), eh (he), ee (she), shin (we), shiu (you pl.), ad (they) (Used as subject/object in verbal constructions)
• my (my)+len, dty (your)+len, e (his)+len, e (her, no len, h- before vowel), nyn (our/your pl./their)+ecl (*my vlein* (my year), *e charrey* (his friend), *e carrey* (her friend))
• Prepositions inflect for person: ec->aym/ayd/echey/eck/ain/eu/oc, er->orrym/ort/er/urree/orrin/erriu/orroo (*t'eh aym* (I have it, lit. it is at-me))
• Relative pronoun not usually expressed; relative clause formed by verb alone or with 'ta' (*yn dooinney haink* (the man who came), *yn ven ta cummal ayns shoh* (the woman who lives here))
• 10 irregular/suppletive verbs: goll (go), cheet (come), cur (give/put), geddyn (get), jannoo (do/make), fakin (see), gra (say), clashtyn (hear), toiggal (understand), ec (at/have) (Each has distinct past, future, conditional, imperative stems)
• cha + lenition + verb for simple negative (*Cha nel mee* (I am not), *Cha jarg mee* (I cannot))
• vel/row/bee etc. for interrogative; nagh for negative interrogative (*Vel oo cheet?* (Are you coming?), *Nagh vel eh ayn?* (Is he not there?))
• Present: ta + subject + verbal noun. Habitual: bee + subject + verbal noun (*Ta mee goll* (I am going), *Bee eh cheet* (He comes [habitually]))
• Past: synthetic past form (often lenited), or ren + subject + VN (*Honnick mee* (I saw), *Ren mee fakin* (I saw [periphrastic]))
• Future: bee/vees + subject + VN, or synthetic future (*Hig eh* (He will come), *Bee eh cheet* (He will be coming))
• Conditional: yinnagh/veagh + subject + VN (*Yinnin shen* (I would do that), *Veagh eh goll* (He would be going))
• Adjectives follow the noun (*thie beg* (small house), *moddey mooar* (big dog))
• Adverbs typically follow the verb or come at end of clause (*Haink eh dy-tappee* (He came quickly))
• Copula sentences: She + predicate + subject (*She Manninagh mee* (I am a Manxman - lit. Is Manxman I))
• Fronting for emphasis using copula cleft: She + fronted element + relative clause (*She ayns Doolish v'eh cummal* (It was in Douglas he was living))
• Genitive noun follows the possessed noun (*dorrys y thie* (the door of the house))
• Basic word order is Verb-Subject-Object (*Honnick yn dooinney yn kayt* (The man saw the cat - lit. saw the man the cat))

Lenition mappings: b -> v; c -> ch; ch/ch -> h; d -> gh; f -> zero (disappears); g -> gh/y; j -> y; m -> v; p -> ph; qu -> wh; s -> h/l/n; str -> hr; t -> h
Eclipsis mappings: b -> m; c/k -> g; d -> n; f -> v; g -> n'gh; j -> n'y; p -> b; t -> d; vowel -> n'+vowel
GRAMMAR;

// --- BUILD PROMPT ---
if ($direction === 'en-gv') {
    $system = "You are an expert translator specialising in Manx Gaelic (Gaelg). You translate English text into modern revived Manx.

Key principles:
- Use modern revived Manx spelling and grammar conventions
- Maintain natural Manx word order (VSO - verb-subject-object)
- Use Manx idiom where possible rather than literal English calques
- For proper nouns with established Manx forms, use them (Mannin, Sostyn, Nerin, Nalbin, Bretin, Divlyn)
- Parliament (Westminster) = Ardwhaiyl, Manx parliament = Tinvaal
- Crown = Crooin, sovereignty = ard-reiltys
- House of Keys = Kiare as Feed, Lord of Mann = Chiarn Vannin
- Keep specialised historical terms in English where no Manx equivalent exists

GRAMMAR RULES:
$grammar

VOCABULARY REFERENCE (Coonceil ny Gaelgey official terms - use these when the English word matches):
$vocabulary

EXAMPLE TRANSLATIONS (for style and register):
$examples

Translate naturally and fluently. Output ONLY the Manx translation, no explanations or notes.";

    $user_msg = "Translate into Manx Gaelic:\n\n$text";
} else {
    $system = "You are an expert translator specialising in Manx Gaelic (Gaelg). You translate Manx text into clear, natural English.

GRAMMAR RULES (to aid comprehension):
$grammar

VOCABULARY REFERENCE:
$vocabulary

EXAMPLE TRANSLATIONS:
$examples

Translate naturally and fluently. Output ONLY the English translation, no explanations or notes.";

    $user_msg = "Translate into English:\n\n$text";
}

// --- CALL ANTHROPIC API ---
$payload = json_encode([
    'model' => 'claude-sonnet-4-20250514',
    'max_tokens' => 2000,
    'system' => $system,
    'messages' => [
        ['role' => 'user', 'content' => $user_msg]
    ]
]);

$ch = curl_init('https://api.anthropic.com/v1/messages');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'x-api-key: ' . $ANTHROPIC_API_KEY,
        'anthropic-version: 2023-06-01'
    ],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 60
]);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curl_error = curl_error($ch);
curl_close($ch);

if ($curl_error) {
    http_response_code(502);
    echo json_encode(['error' => 'Translation service unavailable']);
    exit;
}

if ($http_code !== 200) {
    http_response_code(502);
    echo json_encode(['error' => 'Translation service error']);
    exit;
}

$data = json_decode($response, true);
$translation = '';
foreach (($data['content'] ?? []) as $block) {
    if (($block['type'] ?? '') === 'text') {
        $translation .= $block['text'];
    }
}

if (empty($translation)) {
    http_response_code(500);
    echo json_encode(['error' => 'No translation returned']);
    exit;
}

echo json_encode([
    'translation' => trim($translation),
    'direction' => $direction,
    'model' => 'claude-sonnet-4'
]);
