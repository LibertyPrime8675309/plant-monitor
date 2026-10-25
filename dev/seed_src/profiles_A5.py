"""Plant profiles for the "About this plant" fields (1.14.0, batchA5).

One profile per species or group; build_batchA5.py maps each plant to one. Written by Claude on October 25, 2026 from the
sources listed with each profile (found by web search; links checked to come from the search results) and general botany.
Conservation statuses are only stated where Claude confirmed them (Wikipedia's IUCN line); otherwise the text says none
was confirmed. CITES covers international trade only, not growing a plant at home.
Fields: habit, order, family, genus, hg/wg (height/width in the ground), hp/wp (in a pot), rate, life, zl/zh (USDA zones),
zn (zone notes), native, cons, inv, bloom, fruit, dh (dangers to people), da (dangers to animals), prop (list), src (keys
into srcs.txt), plus extra source tuples in 'more'."""

ASPCA = ('ASPCA Animal Poison Control: Toxic and non-toxic plants', 'https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants')
NO_IUCN = 'No IUCN Red List assessment that Claude could confirm.'
AROID_PEOPLE = ('All parts contain needle-like calcium oxalate crystals. Chewing them causes burning pain and swelling of the mouth, '
                'tongue and throat, drooling and trouble swallowing; the sap can irritate skin and eyes. Rarely serious, but keep it from children '
                'and wash your hands after pruning.')
AROID_PETS = ('Toxic to cats and dogs (ASPCA): the calcium oxalate crystals cause pawing at the mouth, drooling, mouth swelling, vomiting '
              'and trouble swallowing.')
CACTUS_PEOPLE = 'Not poisonous, but the spines (and on some kinds, tiny barbed hairs) lodge in skin. Use thick gloves or folded newspaper to handle it.'
CACTUS_PETS = 'Not poisonous; the danger is spines in mouths, paws and fur.'

P = {}

P['dieffenbachia'] = dict(habit='Evergreen tropical perennial with a thick cane-like stem (an aroid)', order='Alismatales', family='Araceae', genus='Dieffenbachia',
    hg='3 to 6 ft', wg='2 to 3 ft', hp='3 to 5 ft', wp='2 to 3 ft', rate='Moderate to fast in warmth', life='Many years; old canes get leggy and can be cut back',
    zl='10b', zh='12', zn='Leaves are damaged below about 45 to 50°F, so it is a houseplant and summer patio plant here.',
    native='Tropical Central and South America and the Caribbean, in shady, moist forest.', cons=NO_IUCN + ' Garden plants are cultivars.',
    inv='Not a risk here.', bloom='A small greenish-white spathe and spadix, hidden among the leaves; uncommon indoors.', fruit='Small orange-red berries after flowering, rarely seen indoors. Not edible.',
    dh=AROID_PEOPLE + ' Its old name "dumb cane" comes from the mouth swelling, which can stop speech for a while.', da=AROID_PETS,
    prop=['Cane cuttings: cut a bare stem into 2 to 3 in pieces with a node each, lay them half-buried in moist mix, keep warm (70 to 80°F).',
          'Tip cuttings rooted in water or moist mix.', 'Air layering a tall, leggy cane, then cutting it off once roots show.'],
    src=['dieffenbachia'], more=[ASPCA])

P['spathiphyllum'] = dict(habit='Evergreen clump-forming tropical perennial (an aroid)', order='Alismatales', family='Araceae', genus='Spathiphyllum',
    hg='1 to 4 ft (by cultivar)', wg='1 to 3 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Moderate', life='Many years; divide when crowded',
    zl='10', zh='12', zn='Damaged below about 45°F; a houseplant here.',
    native='Tropical Central and South America (most species), with a few in Southeast Asia and the western Pacific.', cons=NO_IUCN + ' Garden plants are cultivars and hybrids.',
    inv='Not a risk here.', bloom='White spathes (often called flowers) on stalks above the leaves, mostly spring and summer, sometimes again in fall. They fade to green.',
    fruit='None worth noting.', dh=AROID_PEOPLE + ' It is not a true lily.', da=AROID_PETS + ' Unlike true lilies (Lilium), it does not cause kidney failure in cats.',
    prop=['Division: lift the clump in spring and pull it apart into pieces with several leaves and roots each.'],
    src=['spathiphyllum'], more=[ASPCA])

P['philo_erubescens'] = dict(habit='Evergreen climbing tropical vine (an aroid); cultivars like Pink Princess and White Knight climb a moss pole', order='Alismatales', family='Araceae', genus='Philodendron',
    hg='Climbs 10 to 20 ft or more on trees', wg='2 to 3 ft', hp='3 to 6 ft on a pole', wp='1.5 to 2.5 ft', rate='Moderate; faster when it can climb', life='Many years',
    zl='10b', zh='12', zn='Damaged below about 50°F; a houseplant here.',
    native='The species, Philodendron erubescens, comes from the rainforests of Colombia. The variegated cultivars are selections kept going by cuttings and tissue culture.',
    cons=NO_IUCN + ' Cultivated plants are cultivars.', inv='Not a risk here.', bloom='A dark red spathe, rare indoors.', fruit='Berries only after pollination; not seen indoors and not edible.',
    dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Stem cuttings with at least one node and an aerial root, rooted in water, moss or moist chunky mix.',
          'For variegated cultivars, cut just above a node with good variegation: the new growth copies the colour of the node it grows from.',
          'Air layering on a moss pole.'],
    src=['erubescens'], more=[ASPCA])

P['philo_hybrid'] = dict(habit='Evergreen tropical aroid, a self-heading or slowly climbing hybrid', order='Alismatales', family='Araceae', genus='Philodendron',
    hg='Not grown in the ground here; 2 to 4 ft where it is', wg='2 to 3 ft', hp='2 to 3 ft', wp='1.5 to 2.5 ft', rate='Slow to moderate', life='Many years',
    zl='10b', zh='12', zn='Damaged below about 50°F; a houseplant here.',
    native='A cultivated hybrid or mutation, with no wild range. Its parents are Philodendron species from tropical Central and South America.',
    cons='Not applicable: a cultivated hybrid.', inv='Not a risk here.', bloom='Rare indoors.', fruit='None indoors.',
    dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Stem or node cuttings rooted in water, moss or moist chunky mix.', 'Separate offshoots (pups) with their own roots from the base.',
          'Many of these hybrids can revert or change pattern when grown from cuttings; tissue-cultured plants keep the look best.'],
    src=['birkin', 'erubescens'], more=[ASPCA])

P['philo_micans'] = dict(habit='Evergreen trailing or climbing tropical vine (an aroid)', order='Alismatales', family='Araceae', genus='Philodendron',
    hg='Climbs 10 to 20 ft on trees', wg='Trails 3 to 6 ft', hp='Trails 2 to 6 ft', wp='1 to 2 ft', rate='Fast in warmth', life='Many years',
    zl='10b', zh='12', zn='Damaged below about 50°F; a houseplant here.',
    native='Philodendron hederaceum grows wild from Mexico and the Caribbean to Brazil. Micans is its velvety-leaved form.',
    cons=NO_IUCN, inv='Can escape and smother native plants in frost-free places such as South Florida and Hawaii; not a risk in Central Texas.',
    bloom='Rare indoors.', fruit='None indoors.', dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Stem cuttings with a node, in water or moist mix; roots form in 2 to 4 weeks.', 'Pin a trailing stem onto moist mix in the same pot to root and fill it out.'],
    src=['hederaceum'], more=[ASPCA])

P['monstera'] = dict(habit='Evergreen climbing tropical vine (an aroid) with aerial roots', order='Alismatales', family='Araceae', genus='Monstera',
    hg='Climbs 30 to 60 ft on trees', wg='3 to 8 ft', hp='6 to 10 ft on a pole', wp='3 to 6 ft', rate='Moderate to fast', life='Decades',
    zl='10', zh='12', zn='Damaged below about 50°F; a houseplant here. Grown outdoors in South Florida and Hawaii.',
    native='Southern Mexico to Panama, in tropical forest.', cons=NO_IUCN, inv='Not a risk in Central Texas.',
    bloom='A cream spathe around a thick spadix, on mature plants; rare indoors.',
    fruit='Mature plants grow a long green fruit, the "fruit salad" fruit. Fully ripe flesh is edible, tasting of pineapple and banana; unripe fruit is full of irritating crystals. Rarely forms indoors.',
    dh=AROID_PEOPLE + ' Only fully ripe fruit is safe to eat.', da=AROID_PETS,
    prop=['Stem cuttings with a node and an aerial root, in water, moss or moist chunky mix.', 'Air layering on a tall plant.', 'Seed, rarely available.'],
    src=['monstera'], more=[ASPCA])

P['syngonium'] = dict(habit='Evergreen climbing tropical vine (an aroid); young plants are compact', order='Alismatales', family='Araceae', genus='Syngonium',
    hg='Climbs 6 to 30 ft when mature', wg='Spreads widely', hp='1 to 3 ft (6 ft on a pole)', wp='1 to 2 ft', rate='Fast', life='Many years',
    zl='10', zh='12', zn='Damaged below about 50°F; a houseplant here.',
    native='Syngonium podophyllum grows wild from Mexico through Central America to Bolivia and Brazil.', cons=NO_IUCN,
    inv='Listed as invasive in Florida, where it smothers native plants. Keep cuttings out of compost and the wild; not a risk in Central Texas winters.',
    bloom='Rare indoors.', fruit='None indoors.', dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Stem cuttings with a node, in water or moist mix.', 'Division of a crowded pot.'],
    src=['syngonium'], more=[ASPCA])

P['aglaonema'] = dict(habit='Evergreen clump-forming tropical perennial (an aroid)', order='Alismatales', family='Araceae', genus='Aglaonema',
    hg='1 to 3 ft', wg='1 to 3 ft', hp='1 to 2 ft', wp='1 to 2 ft', rate='Slow', life='Many years',
    zl='10b', zh='12', zn='Damaged below about 50°F, and red kinds can be hurt by cold drafts even above that.',
    native='Tropical and subtropical Asia, from India and southern China to New Guinea, on shady forest floors. Red kinds are cultivated hybrids.',
    cons='Not applicable for cultivated hybrids. ' + NO_IUCN, inv='Not a risk here.', bloom='A small greenish-white spathe, occasionally indoors.',
    fruit='Red berries after flowering, sometimes indoors. Not edible.', dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Division of the clump when repotting.', 'Stem or tip cuttings, in water or moist mix.'],
    src=['aglaonema'], more=[ASPCA])

P['alocasia'] = dict(habit='Tropical perennial from a rhizome or corm (an aroid); can go dormant in cool or dry spells', order='Alismatales', family='Araceae', genus='Alocasia',
    hg='2 to 6 ft (by cultivar)', wg='2 to 4 ft', hp='2 to 4 ft', wp='1.5 to 3 ft', rate='Fast in summer, slow or dormant in winter', life='Many years; the corm survives dormancy',
    zl='10a', zh='11', zn='Leaves are damaged below about 50°F. A dormant plant loses its leaves but can regrow from the corm in spring if kept just moist.',
    native='The genus grows wild from tropical Asia to eastern Australia. Houseplant kinds like these are mostly cultivated hybrids.',
    cons='Not applicable for cultivated hybrids.', inv='Not a risk here.', bloom='A cream spathe, occasional on mature plants.', fruit='Red berries after flowering. Not edible.',
    dh=AROID_PEOPLE, da=AROID_PETS,
    prop=['Separate offset corms ("bulbils") found in the soil when repotting, and start them in damp moss or perlite.', 'Divide clumps in spring.'],
    src=['alocasia'], more=[ASPCA])

P['zz'] = dict(habit='Evergreen tropical perennial from thick underground rhizomes (an aroid)', order='Alismatales', family='Araceae', genus='Zamioculcas',
    hg='2 to 3 ft', wg='2 to 3 ft', hp='2 to 3 ft', wp='1.5 to 2.5 ft', rate='Slow', life='Many years',
    zl='10', zh='12', zn='Damaged below about 45°F. Very drought tolerant because the rhizomes store water.',
    native='Eastern Africa: Kenya, Tanzania, Malawi, Mozambique, Zimbabwe and KwaZulu-Natal in South Africa, in dry grassland and forest.',
    cons='No global IUCN assessment confirmed. Listed as Least Concern in South Africa by SANBI.', inv='Not a risk here.',
    bloom='A small cream spathe low among the stems, occasionally on older plants.', fruit='Rarely sets fruit.',
    dh='Contains calcium oxalate crystals. Chewing causes mouth and throat irritation; the sap can irritate skin. Not as dangerous as its reputation online suggests, but keep it from children.',
    da=AROID_PETS,
    prop=['Division of the rhizomes when repotting.', 'Single leaflets or whole stems pushed into moist gritty mix; slow, often 6 months or more to grow a new rhizome.'],
    src=['zz'], more=[ASPCA])

P['calathea'] = dict(habit='Evergreen clump-forming tropical perennial (a prayer plant: leaves fold up at night)', order='Zingiberales', family='Marantaceae', genus='Goeppertia (formerly Calathea)',
    hg='1 to 3 ft', wg='1 to 2 ft', hp='1 to 2 ft', wp='1 to 2 ft', rate='Moderate', life='Many years if kept humid',
    zl='11', zh='12', zn='Damaged below about 55 to 60°F. Needs humid air and soft water.',
    native='Tropical Central and South America, on the floor of rainforests.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Small flowers in bracts near the base on some kinds; the leaves are the show.', fruit='None indoors.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists Calathea as non-toxic).',
    prop=['Division in spring: separate clumps with several leaves and their own roots.'], src=['calathea'], more=[ASPCA])

P['phalaenopsis'] = dict(habit='Epiphytic orchid: grows on tree branches, with thick aerial roots', order='Asparagales', family='Orchidaceae', genus='Phalaenopsis',
    hg='Leaves 6 to 12 in; flower spikes 1 to 3 ft', wg='1 to 1.5 ft', hp='1 to 3 ft with spike', wp='1 ft', rate='Slow: a few leaves a year', life='Decades',
    zl='10b', zh='12', zn='Damaged below about 55°F. A cool spell of about 60°F at night in fall helps it set a flower spike.',
    native='Tropical Asia and the western Pacific: the Himalayas, southern China, Southeast Asia, the Philippines, Indonesia, New Guinea and northern Australia. Shop plants are hybrids.',
    cons='All orchids are on CITES Appendix II, which controls international trade in wild plants. Shop hybrids are artificially propagated.',
    inv='Not a risk here.', bloom='Long arching sprays of flat flowers that last 2 to 4 months, usually winter to spring.', fruit='None unless hand-pollinated.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists Phalaenopsis as non-toxic).',
    prop=['Keikis: baby plants that sometimes grow on the flower spike; detach once they have 2 to 3 roots about 2 in long.',
          'Commercially grown from seed or tissue culture in sterile labs; not practical at home.'],
    src=['phalaenopsis'], more=[ASPCA])

P['nephrolepis'] = dict(habit='Evergreen fern, with arching fronds and running stolons', order='Polypodiales', family='Nephrolepidaceae', genus='Nephrolepis',
    hg='2 to 3 ft', wg='2 to 4 ft', hp='1 to 3 ft', wp='2 to 3 ft', rate='Fast', life='Many years; divide when crowded',
    zl='9b', zh='11', zn='Fronds are damaged by frost; roots can survive light freezes in the ground in zone 9b.',
    native='Tropical and subtropical Americas, including Florida, Mexico, the Caribbean and northern South America, as well as parts of Africa and Polynesia. Boston fern is a selection of it.',
    cons=NO_IUCN, inv='Its cousin, sword fern (Nephrolepis cordifolia), is invasive in Florida. Boston fern cultivars spread mostly in pots.',
    bloom='None: ferns reproduce by spores, which are the brown dots under the fronds.', fruit='None.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists Boston fern as non-toxic).',
    prop=['Division of the crown.', 'Pin down the runners (stolons) onto moist mix; each rooted tip becomes a new plant.'],
    src=['nephrolepis'], more=[ASPCA])

P['begonia'] = dict(habit='Evergreen tropical perennial; a cane-stemmed or shrubby begonia', order='Cucurbitales', family='Begoniaceae', genus='Begonia',
    hg='1 to 4 ft (cane types can be taller)', wg='1 to 2 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Moderate to fast', life='Several years; refresh from cuttings when leggy',
    zl='10', zh='11', zn='Damaged below about 50°F; a houseplant here.',
    native='The genus is tropical, mainly Central and South America, Africa and Asia. Polka-dot begonia (Begonia maculata) is from Brazil; cultivars like Obsidian are hybrids.',
    cons='Not applicable for hybrids. ' + NO_IUCN, inv='Not a risk here.', bloom='Clusters of small white, pink or red flowers, often much of the year indoors.',
    fruit='Small winged capsules; not edible.', dh='Mildly poisonous: the plant contains soluble oxalates, most of all in the roots and tubers. Chewing can irritate the mouth.',
    da='Toxic to cats and dogs (ASPCA): oxalates cause mouth irritation, drooling and vomiting, worst from the underground parts.',
    prop=['Stem cuttings with 2 to 3 nodes, in water or moist mix.', 'Leaf cuttings for some kinds.'],
    src=['begonia'], more=[ASPCA])

P['coleus'] = dict(habit='Tender perennial grown as an annual, with soft square stems (mint family)', order='Lamiales', family='Lamiaceae', genus='Coleus (formerly Plectranthus or Solenostemon)',
    hg='1 to 3 ft', wg='1 to 2 ft', hp='1 to 2 ft', wp='1 to 1.5 ft', rate='Fast', life='One season outdoors; kept going for years from cuttings',
    zl='10', zh='11', zn='Killed by frost and sulks below about 50°F.',
    native='Southeast Asia and the western Pacific, from Malaysia to Australia. The colourful kinds are cultivars.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Spikes of small blue or lavender flowers in late summer. Pinch them off to keep the leaves bushy.', fruit='Tiny nutlets; not edible.',
    dh='Not considered poisonous to people; the sap can irritate sensitive skin.', da='Toxic to cats and dogs (ASPCA): essential oils cause vomiting and diarrhea, and sometimes depression.',
    prop=['Stem tip cuttings root in a week or two in water or moist mix: an easy way to keep favourite colours over winter.', 'Seed, for seed-grown strains.'],
    src=['coleus'], more=[ASPCA])

P['ficus_elastica'] = dict(habit='Evergreen tropical tree with milky sap', order='Rosales', family='Moraceae', genus='Ficus',
    hg='50 to 100 ft in the wild', wg='Wide, with aerial roots', hp='6 to 10 ft', wp='2 to 4 ft', rate='Moderate to fast in bright light', life='Decades',
    zl='10b', zh='12', zn='Damaged below about 35 to 40°F; a houseplant here.',
    native='Eastern South and Southeast Asia: Nepal and northeastern India through Myanmar, Thailand, Yunnan in China and Malaysia to Indonesia.',
    cons='Least Concern (IUCN).', inv='Not a risk here.', bloom='Tiny flowers hidden inside figs; not seen indoors.', fruit='Small yellow-green figs on old outdoor trees only. Not eaten.',
    dh='The milky sap (latex) irritates skin and eyes and can trigger latex allergy. Wear gloves when pruning.',
    da='Toxic to cats and dogs (ASPCA lists rubber plant): the sap causes mouth irritation, vomiting and skin irritation.',
    prop=['Air layering a branch (the most reliable way).', 'Tip cuttings in warm, humid conditions; let the sap stop bleeding first.'],
    src=['elastica'], more=[ASPCA])

P['ficus_lyrata'] = dict(habit='Evergreen tropical tree with large fiddle-shaped leaves and milky sap', order='Rosales', family='Moraceae', genus='Ficus',
    hg='30 to 40 ft outdoors in the tropics', wg='15 to 25 ft', hp='6 to 10 ft', wp='2 to 4 ft', rate='Moderate in bright light', life='Decades',
    zl='10b', zh='12', zn='Damaged below about 40°F; a houseplant here.',
    native='Western and Central Africa, in lowland rainforest: from Sierra Leone and Liberia east to Cameroon and Gabon.', cons='Least Concern (IUCN).',
    inv='Not a risk here.', bloom='Tiny flowers hidden inside figs; not seen indoors.', fruit='Small green figs on old outdoor trees only. Not eaten.',
    dh='The milky sap irritates skin and eyes. Wear gloves when pruning.', da='Toxic to cats and dogs (ASPCA lists Ficus): mouth irritation, vomiting and skin irritation.',
    prop=['Air layering.', 'Stem cuttings with a leaf or two, in warm humid conditions.'],
    src=['lyrata'], more=[ASPCA])

P['ficus_carica'] = dict(habit='Deciduous fruit tree or large shrub', order='Rosales', family='Moraceae', genus='Ficus',
    hg='10 to 30 ft', wg='10 to 30 ft', hp='4 to 8 ft', wp='3 to 6 ft', rate='Fast', life='Decades',
    zl='7b', zh='10', zn='Hardy in the ground in Central Texas. Young trees can be frozen to the ground in a hard freeze and regrow from the roots.',
    native='Southwest Asia and the eastern Mediterranean; grown for thousands of years.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='No visible flowers: the tiny flowers are inside the developing fig.',
    fruit='Edible figs, usually summer and sometimes again in fall. Common figs in Texas set fruit without pollination.',
    dh='The milky sap irritates skin and, with sunlight, can cause blistering burns (phytophotodermatitis). Wear gloves and long sleeves when pruning.',
    da='The leaves and sap are toxic to cats and dogs (ASPCA): vomiting, drooling and skin irritation. Ripe fruit in small amounts is not a known danger.',
    prop=['Hardwood cuttings in late winter, pencil-thick and 8 to 10 in long, set mostly into the soil.', 'Softwood cuttings in early summer.', 'Air layering or ground layering a low branch.'],
    src=['fig'], more=[ASPCA])

P['pachira'] = dict(habit='Evergreen tropical tree, often sold with braided trunks', order='Malvales', family='Malvaceae', genus='Pachira',
    hg='30 to 60 ft in the wild', wg='15 to 30 ft', hp='4 to 8 ft', wp='2 to 4 ft', rate='Moderate', life='Decades',
    zl='10b', zh='12', zn='Damaged below about 40°F; a houseplant here.',
    native='Central and South America, in freshwater swamps and along rivers, from southern Mexico to northern Brazil.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Large flowers with long cream to red stamens, like a shaving brush; on outdoor trees only.',
    fruit='Large woody pods with nut-like seeds. The seeds are eaten roasted in its native range; raw seeds are not recommended.',
    dh='Not considered poisonous.', da='Non-toxic to cats and dogs (ASPCA lists money tree as non-toxic).',
    prop=['Stem cuttings in warmth and humidity.', 'Seed, when fresh.'], src=['pachira'], more=[ASPCA])

P['ravenea'] = dict(habit='Palm with a single trunk and feathery fronds', order='Arecales', family='Arecaceae', genus='Ravenea',
    hg='Up to about 100 ft in the wild', wg='10 to 15 ft', hp='10 to 12 ft over many years', wp='4 to 6 ft', rate='Moderate; slower indoors', life='Decades',
    zl='9b', zh='11', zn='Fronds are damaged below about 30°F; young potted plants should come in before frost.',
    native='Southwestern Madagascar, in humid pockets along rivers, lagoons and swamps in otherwise dry country.', cons='Vulnerable (IUCN).',
    inv='Not a risk here.', bloom='Small cream flowers in clusters, on separate male and female trees; rare in pots.', fruit='Small red fruits on female trees, rare in pots. Not eaten.',
    dh='Not known to be poisonous.', da='Not known to be poisonous to pets.',
    prop=['Seed only (it does not make offsets). Fresh seed sprouts in 1 to 3 months in warmth. Pots often hold several seedlings grown together.'],
    src=['ravenea'], more=[ASPCA])

P['adenium'] = dict(habit='Succulent shrub or small tree with a swollen water-storing trunk base (caudex)', order='Gentianales', family='Apocynaceae', genus='Adenium',
    hg='3 to 10 ft (up to 16 ft for some)', wg='3 to 5 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Slow', life='Decades',
    zl='10b', zh='12', zn='Damaged below about 40°F and rots if cold and wet. Keep dry and warm in winter; it may drop its leaves and rest.',
    native='The Sahel south of the Sahara from Senegal to Sudan, eastern and southern tropical Africa, and the Arabian Peninsula.',
    cons='Least Concern (IUCN).', inv='Not a risk here.',
    bloom='Trumpet flowers in pink, red or white, mostly spring to fall.', fruit='Long paired seed pods with fluffy seeds. Not edible.',
    dh='Highly poisonous: all parts, and especially the milky sap, contain cardiac glycosides that affect the heart. It has been used as an arrow poison. Wear gloves, keep sap off skin and eyes, and keep it away from children.',
    da='Highly toxic to pets and livestock: vomiting, drooling, abnormal heart rhythm and possibly death. Keep pets away from it.',
    prop=['Seed: sprouts in a week in warmth, and seedlings form a fat caudex.', 'Stem cuttings, dried for a few days first; cuttings rarely form a thick caudex.', 'Grafting choice flower colours onto seedling stock.'],
    src=['adenium'], more=[ASPCA])

P['euphorbia_milii'] = dict(habit='Spiny succulent shrub', order='Malpighiales', family='Euphorbiaceae', genus='Euphorbia',
    hg='2 to 6 ft', wg='1.5 to 3 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Slow to moderate', life='Decades',
    zl='10', zh='12', zn='Damaged below about 35°F; bring it in before frost.',
    native='Madagascar.', cons=NO_IUCN + ' Succulent Euphorbia species are on CITES Appendix II, which controls international trade, with exemptions for nursery-grown hybrids of this one.',
    inv='Not a risk here.', bloom='Small flowers surrounded by bright red, pink or yellow bracts, much of the year in good light.', fruit='Small capsules; not edible.',
    dh='The milky sap irritates skin and is dangerous in the eyes (it can cause painful inflammation). Poisonous if eaten. Sharp thorns. Wear gloves and eye protection when pruning.',
    da='Toxic to cats and dogs (ASPCA lists crown of thorns): mouth irritation, vomiting and diarrhea; the sap irritates skin and eyes.',
    prop=['Stem cuttings: let the sap stop (dip the cut in water), dry for a few days, then root in gritty mix.'],
    src=['milii'], more=[ASPCA])

P['aloe_vera'] = dict(habit='Stemless succulent forming clumps of fleshy rosettes', order='Asparagales', family='Asphodelaceae', genus='Aloe',
    hg='1 to 2 ft (3 ft in flower)', wg='1 to 2 ft, spreading by pups', hp='1 to 2 ft', wp='1 to 2 ft', rate='Moderate', life='Many years; the clump keeps going by pups',
    zl='9b', zh='11', zn='Damaged below about 28 to 32°F; protect it or bring it in on freezing nights.',
    native='Known only in cultivation for centuries; probably from the Arabian Peninsula.',
    cons='Aloe species are on CITES Appendix II, but Aloe vera itself is exempt.', inv='Not a risk here.',
    bloom='Tall spikes of yellow tube flowers, mostly late winter to spring, on older plants in good light.', fruit='Small capsules; not edible.',
    dh='The clear inner gel is widely used on skin. The yellow sap just under the leaf skin (aloe latex) is a strong laxative and should not be eaten.',
    da='Toxic to cats and dogs (ASPCA): saponins and anthraquinones cause vomiting, diarrhea and lethargy.',
    prop=['Separate pups (offsets) with some roots, let them dry a day, and pot them in gritty mix.'],
    src=['aloe'], more=[ASPCA])

P['aloe_dwarf'] = dict(habit='Small clumping succulent rosette (a dwarf aloe hybrid)', order='Asparagales', family='Asphodelaceae', genus='Aloe (or ×Gasteraloe)',
    hg='4 to 8 in (1 ft in flower)', wg='6 to 12 in, spreading by pups', hp='4 to 8 in', wp='6 to 12 in', rate='Moderate', life='Many years',
    zl='9b', zh='11', zn='Damaged below about 28 to 32°F.', native='A cultivated hybrid, with no wild range. Its parents are dwarf aloes from Madagascar and southern Africa.',
    cons='Not applicable: a cultivated hybrid.', inv='Not a risk here.', bloom='Thin spikes of orange to coral tube flowers.', fruit='None of note.',
    dh='Not known to be seriously poisonous; do not eat it.', da='Aloes are listed as toxic to cats and dogs (ASPCA): vomiting and diarrhea if chewed.',
    prop=['Separate pups with roots.'], src=['aloe'], more=[ASPCA])

P['aloiampelos'] = dict(habit='Scrambling succulent shrub with thin stems (a rambling aloe)', order='Asparagales', family='Asphodelaceae', genus='Aloiampelos (formerly Aloe)',
    hg='3 to 6 ft', wg='4 to 6 ft', hp='2 to 3 ft', wp='2 to 3 ft', rate='Moderate to fast', life='Many years',
    zl='8a', zh='11', zn='One of the hardiest aloes: takes frost down to about 10 to 15°F, so it can usually stay out in Round Rock with a frost cloth on the hardest nights.',
    native='The Eastern Cape and nearby mountains of South Africa and Lesotho.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Heads of yellow to orange tube flowers in late spring to summer; loved by hummingbirds.', fruit='Small capsules; not edible.',
    dh='Not known to be seriously poisonous; do not eat it.', da='Aloes are listed as toxic to cats and dogs (ASPCA): vomiting and diarrhea if chewed.',
    prop=['Stem cuttings root easily once dried for a few days.', 'Seed.'], src=['striatula'], more=[ASPCA])

P['haworthiopsis'] = dict(habit='Small stemless succulent rosette, forming clumps', order='Asparagales', family='Asphodelaceae', genus='Haworthiopsis',
    hg='4 to 8 in', wg='6 to 12 in, spreading by pups', hp='4 to 6 in', wp='6 to 10 in', rate='Slow', life='Many years',
    zl='9b', zh='11', zn='Damaged below about 30°F. Prefers bright shade to full sun.', native='The Eastern Cape of South Africa.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Thin wiry stalks of tiny white flowers, often in summer.', fruit='None of note.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists Haworthia as non-toxic).',
    prop=['Separate pups with roots when repotting.', 'Leaf cuttings, slowly.'], src=['haworthia'], more=[ASPCA])

P['portulacaria'] = dict(habit='Succulent shrub with small round leaves on red-brown stems', order='Caryophyllales', family='Didiereaceae', genus='Portulacaria',
    hg='6 to 12 ft in the wild', wg='4 to 6 ft', hp='1 to 3 ft (trails in hanging pots)', wp='1 to 2 ft', rate='Slow to moderate (variegated forms are slower)', life='Decades',
    zl='9b', zh='11', zn='Damaged below about 30°F.', native='South Africa and Mozambique, in dry thicket where elephants and tortoises browse it.', cons=NO_IUCN,
    inv='Not a risk here.', bloom='Tiny pink flowers, rare on potted plants.', fruit='None of note.',
    dh='Not poisonous; the leaves are eaten in salads in southern Africa. Do not confuse it with jade plant (Crassula ovata), which looks similar and is toxic to pets.',
    da='Not known to be poisonous to pets.', prop=['Stem cuttings, dried for a day or two, root easily in gritty mix.'], src=['portulacaria'])

P['aeonium_arboreum'] = dict(habit='Branching succulent subshrub with rosettes at the stem tips', order='Saxifragales', family='Crassulaceae', genus='Aeonium',
    hg='2 to 4 ft', wg='2 to 3 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Moderate; grows in the cool season and rests in summer heat', life='Several years; a rosette dies after it flowers, the branches go on',
    zl='9b', zh='11', zn='Damaged below about 28°F, and sulks in Texas summer heat: give it afternoon shade then.',
    native='The Canary Islands, especially Gran Canaria; naturalised around the Mediterranean.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Cone-shaped clusters of yellow flowers from mature rosettes in late winter or spring.', fruit='None of note.',
    dh='Not known to be poisonous.', da='Not known to be poisonous to pets.',
    prop=['Cut a rosette with 2 to 4 in of stem, let it dry a few days, and set it in gritty mix.'], src=['aeonium'])

P['aeonium_haworthii'] = dict(P['aeonium_arboreum'], habit='Shrubby succulent with many small rosettes', hg='1 to 2 ft', wg='1 to 2 ft', hp='1 to 1.5 ft', wp='1 to 1.5 ft',
    native='Tenerife, in the Canary Islands, on cliffs.', bloom='Loose clusters of pale yellow to pinkish flowers in spring.',
    src=['aeoniumh', 'aeonium'])

P['graptosedum'] = dict(habit='Small trailing succulent with rosettes (a hybrid of Graptopetalum and Sedum)', order='Saxifragales', family='Crassulaceae', genus='×Graptosedum',
    hg='6 to 8 in', wg='1 to 2 ft, trailing', hp='6 in', wp='1 ft', rate='Moderate', life='Many years',
    zl='8a', zh='11', zn='Takes light frost; protect it below about 20°F.', native='A cultivated hybrid, with no wild range. Its parents are from Mexico.', cons='Not applicable: a cultivated hybrid.',
    inv='Not a risk here.', bloom='Small yellow star flowers in spring.', fruit='None of note.', dh='Not known to be poisonous.', da='Not known to be poisonous to pets.',
    prop=['Single leaves laid on dry gritty mix root and grow tiny rosettes.', 'Stem cuttings.'], src=['grapto'])

P['opuntia'] = dict(habit='Cactus with flat jointed pads', order='Caryophyllales', family='Cactaceae', genus='Opuntia',
    hg='3 to 15 ft (by species)', wg='3 to 10 ft', hp='2 to 4 ft', wp='2 to 3 ft', rate='Moderate to fast', life='Decades',
    zl='8b', zh='11', zn='Opuntia ficus-indica is damaged in hard freezes below about 15 to 20°F. Native Texas prickly pears (Opuntia engelmannii) are hardier.',
    native='Opuntia ficus-indica is from Mexico, domesticated there long ago and now grown worldwide. The genus is native from Canada to Argentina, including Texas.',
    cons='All cacti are on CITES Appendix II, which controls international trade. ' + NO_IUCN, inv='Opuntia ficus-indica is a serious invasive in Australia and South Africa; not a concern in Texas, where prickly pears are native.',
    bloom='Large yellow to orange cup flowers in spring.', fruit='Edible fruit ("tunas"), and young pads ("nopales") are eaten as a vegetable once the spines and glochids are removed.',
    dh='Not poisonous, but besides the large spines it has glochids: tiny barbed hairs that come off in clusters and are hard to remove from skin. Use tongs and thick gloves; tape lifts glochids.',
    da=CACTUS_PETS, prop=['Pad cuttings: cut a pad at the joint, let it callus for a week, and set it upright in dry gritty soil.', 'Seed.'],
    src=['opuntia'], more=[ASPCA])

P['agave'] = dict(habit='Succulent rosette with stiff, spine-tipped leaves; most kinds flower once and die after many years', order='Asparagales', family='Asparagaceae', genus='Agave',
    hg='1 to 6 ft (by species)', wg='2 to 10 ft', hp='1 to 3 ft', wp='1 to 3 ft', rate='Slow to moderate', life='10 to 30 years until it flowers; pups carry on',
    zl='8a', zh='11', zn='Depends on the species, which is not known yet: Agave parryi is hardy to about zone 6, Agave ovatifolia to zone 7 and Agave americana to zone 8. All three do well in the ground in Round Rock in fast-draining soil.',
    native='The Americas, from the southwestern US (including Texas) through Mexico, the main centre, to northern South America.', cons=NO_IUCN + ' (depends on the species).',
    inv='Agave americana has naturalised in some dry places abroad; not a concern here.', bloom='A single huge flower stalk, once, after many years; then the rosette dies.', fruit='Seed capsules after flowering.',
    dh='The sap contains calcium oxalate crystals and saponins that cause itchy, burning rashes; the leaf tips and edges are sharp enough to cause deep punctures. Wear eye protection and gloves when cutting it.',
    da='Mildly toxic to pets if chewed (mouth irritation, vomiting), and the spines can injure them.',
    prop=['Separate pups from the base with some root.', 'Bulbils that form on the flower stalk of some kinds.', 'Seed.'], src=['agave'], more=[ASPCA])

P['myrtillocactus'] = dict(habit='Columnar cactus; this cultivar has smooth, nearly spineless, bumpy stems', order='Caryophyllales', family='Cactaceae', genus='Myrtillocactus',
    hg='The species reaches 13 to 16 ft; this slow cultivar much less', wg='Branches into a candelabra', hp='1 to 3 ft', wp='1 ft', rate='Slow', life='Decades',
    zl='9b', zh='11', zn='Damaged below about 28°F; bring potted plants in on cold nights.',
    native='Central and northern Mexico. This cultivar, Fukurokuryuzinboku, is a cultivated form from Japan.', cons='All cacti are on CITES Appendix II, which controls international trade. ' + NO_IUCN,
    inv='Not a risk here.', bloom='Small creamy flowers on mature stems.', fruit='Small dark purple berries ("garambullos"), eaten in Mexico; rare on young pot plants.',
    dh='Not poisonous; this cultivar has few or no spines.', da='Not poisonous to pets.', prop=['Stem cuttings dried for a week or two, then set in dry gritty mix.', 'Grafting.'],
    src=['myrtillo'])

P['moon_cactus'] = dict(habit='Grafted cactus: a coloured top (scion) on a green rootstock', order='Caryophyllales', family='Cactaceae', genus='Gymnocalycium (top) on a rootstock, often Hylocereus',
    hg='The pair is usually 3 to 8 in', wg='2 to 3 in', hp='3 to 8 in', wp='2 to 3 in', rate='Slow', life='Often only a few years, because the red top has no chlorophyll and depends on the rootstock',
    zl='10b', zh='11', zn='The usual rootstock is tropical and is damaged below about 50°F.',
    native='Gymnocalycium mihanovichii is from Paraguay and northeastern Bolivia. The bright red and yellow forms are mutants with no green, kept alive only by grafting.',
    cons='Least Concern (IUCN). All cacti are on CITES Appendix II.', inv='Not a risk here.', bloom='Pink flowers from the top in summer, sometimes.', fruit='None of note.',
    dh=CACTUS_PEOPLE, da=CACTUS_PETS, prop=['Graft offsets from the coloured top onto a new rootstock: it cannot live on its own roots.'],
    src=['moon', 'cites'])

P['bougainvillea'] = dict(habit='Thorny evergreen woody vine or shrub, grown on a support or as a pot shrub', order='Caryophyllales', family='Nyctaginaceae', genus='Bougainvillea',
    hg='15 to 30 ft as a vine', wg='10 to 20 ft', hp='3 to 6 ft', wp='3 to 5 ft', rate='Fast in heat', life='Decades',
    zl='9b', zh='11', zn='Leaves are damaged near 32°F; the top is killed in the mid-20s °F. In the ground in zone 9a it may come back from the roots after a freeze.',
    native='South America: eastern Brazil south to Argentina and Peru. Garden kinds are mostly hybrids.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Papery bracts in magenta, red, orange, pink or white around tiny white flowers, in flushes from spring to fall; blooms best when slightly dry and root-bound.',
    fruit='Small, rarely seen; not edible.', dh='Sharp thorns can cause puncture wounds that get infected; the sap can cause mild skin irritation in some people.',
    da='Not considered seriously poisonous; chewing leaves may upset a pet\'s stomach, and the thorns can injure.',
    prop=['Semi-hardwood cuttings in late spring to summer, with rooting hormone and bottom heat.', 'Layering a low branch.'], src=['bougainvillea'], more=[ASPCA])

P['grape'] = dict(habit='Deciduous woody vine climbing with tendrils', order='Vitales', family='Vitaceae', genus='Vitis',
    hg='Climbs 40 ft or more into trees', wg='Spreads widely', hp='Needs a trellis; 6 to 10 ft in a big container', wp='3 to 6 ft', rate='Very fast', life='Decades',
    zl='7a', zh='9b', zn='A native of Central Texas, fully hardy here.',
    native='Texas and nearby states (Oklahoma, Louisiana, Arkansas, Alabama); common in Central Texas along creeks and fencerows.', cons=NO_IUCN + ' Common in its range.',
    inv='Native here, but it can smother trees and shrubs if left unchecked.', bloom='Small fragrant greenish flowers in spring.',
    fruit='Dark purple grapes in summer. Edible but very sour, with thick skin that can burn the mouth and hands; traditionally used for jelly and wine with lots of sugar.',
    dh='The fruit skins and juice can irritate skin and mouth. Otherwise not poisonous.',
    da='Grapes and raisins can cause sudden kidney failure in dogs, and possibly cats, even in small amounts. Keep dogs away from fallen fruit.',
    prop=['Hardwood cuttings in winter.', 'Layering a long cane into the soil.', 'Seed, though many seedlings are male and fruitless.'], src=['grape'], more=[ASPCA])

P['ipomoea_hederacea'] = dict(habit='Annual twining vine', order='Solanales', family='Convolvulaceae', genus='Ipomoea',
    hg='Climbs 6 to 10 ft', wg='3 to 6 ft', hp='Climbs 6 ft on a trellis', wp='2 to 3 ft', rate='Very fast', life='One season (annual); reseeds',
    zl='', zh='', zn='An annual: killed by frost and comes back from seed.',
    native='Tropical America. Botanists disagree on whether it is also native to the southeastern US; it is common in Texas.', cons=NO_IUCN,
    inv='A weed of crops and gardens across the southern US; deadhead or pull seedlings to stop it spreading.', bloom='Sky-blue to purple funnel flowers that open in the morning, summer to fall.',
    fruit='Round seed capsules. Not edible.', dh='The seeds contain LSA-type alkaloids and are poisonous: hallucinations, nausea and diarrhea if eaten. Keep them from children.',
    da='Toxic to pets (ASPCA lists morning glory): the seeds cause vomiting, diarrhea, agitation and tremors.',
    prop=['Seed: nick or soak the hard seeds overnight and sow after the last frost.'], src=['ivyleaf'], more=[ASPCA])

P['ipomoea_batatas'] = dict(habit='Trailing tender perennial vine grown for its leaves', order='Solanales', family='Convolvulaceae', genus='Ipomoea',
    hg='6 to 12 in', wg='Trails 3 to 10 ft', hp='Trails over the edge 3 to 6 ft', wp='2 to 4 ft', rate='Very fast in heat', life='One season outdoors; the tubers can be stored',
    zl='9b', zh='11', zn='Killed by frost; the tubers survive in the ground only where the soil does not freeze. Lift them or take cuttings before frost.',
    native='Tropical Central and South America, where sweet potato was domesticated thousands of years ago.', cons='Not applicable: a crop plant and its ornamental cultivars.',
    inv='Not a risk here.', bloom='Rarely flowers; lavender morning-glory flowers in warm climates.',
    fruit='No fruit. Ornamental kinds still form tubers that are edible but bland or bitter; they are bred for leaves, not eating.',
    dh='Not poisonous.', da='Generally regarded as non-toxic; large amounts of leaves may upset a pet\'s stomach.',
    prop=['Stem cuttings root in days in water.', 'Overwinter a tuber indoors and grow slips from it in spring.'], src=['batatas'], more=[ASPCA])

P['caesalpinia'] = dict(habit='Evergreen shrub or small tree in the pea family; thornless', order='Fabales', family='Fabaceae', genus='Erythrostemon (formerly Caesalpinia)',
    hg='6 to 15 ft', wg='6 to 10 ft', hp='4 to 6 ft', wp='3 to 4 ft', rate='Moderate to fast', life='Decades',
    zl='8b', zh='11', zn='Takes light freezes; may lose leaves or die back in hard freezes and regrow.',
    native='Northeastern Mexico and the lower Rio Grande Valley of Texas.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Long spikes of bright yellow flowers spring to fall; attracts butterflies and hummingbirds.', fruit='Flat brown seed pods that split open. Not edible.',
    dh='The seeds and pods of Caesalpinia and its relatives are reported to be poisonous if eaten (vomiting and diarrhea). Keep them from children.',
    da='The seeds and pods may upset pets\' stomachs if chewed; keep them away from fallen pods.',
    prop=['Seed: nick the hard coat or soak overnight before sowing in warm soil.', 'Semi-hardwood cuttings, with difficulty.'], src=['caesalpinia'])

P['rose_flori'] = dict(habit='Deciduous flowering shrub with prickly canes (a floribunda rose)', order='Rosales', family='Rosaceae', genus='Rosa',
    hg='3 to 4 ft', wg='2 to 3 ft', hp='2 to 3 ft', wp='2 ft', rate='Moderate to fast', life='Many years',
    zl='5', zh='9', zn='Hardy in Central Texas. Prune in mid-February, as the Texas A&M AgriLife Extension recommends for the area.',
    native='A cultivated hybrid, with no wild range. Wild roses grow across the Northern Hemisphere.', cons='Not applicable: a cultivated hybrid.',
    inv='Not a risk here.', bloom='Clusters of flowers in repeated flushes from spring to fall.', fruit='Rose hips may form if old flowers are left on; edible when ripe (used for tea), but remove the hairy seeds.',
    dh='Not poisonous. The prickles can carry soil fungi into scratches (rose gardener\'s disease, sporotrichosis), so wear gloves.',
    da='Non-toxic to cats and dogs (ASPCA lists rose as non-toxic); the prickles can injure. Garden sprays used on roses can be toxic.',
    prop=['Softwood or semi-hardwood cuttings in a humid spot; patented cultivars may not be propagated for sale.', 'Ground layering a low cane.'],
    src=['rose'], more=[ASPCA])

P['rose_mini'] = dict(P['rose_flori'], habit='Deciduous flowering shrub, miniature or patio rose', hg='1 to 2 ft', wg='1 to 2 ft', hp='1 to 1.5 ft', wp='1 ft',
    bloom='Small flowers in repeated flushes from spring to fall.')

P['cosmos'] = dict(habit='Annual wildflower in the daisy family', order='Asterales', family='Asteraceae', genus='Cosmos',
    hg='2 to 6 ft (Cosmos bipinnatus); 1 to 4 ft (Cosmos sulphureus)', wg='1 to 3 ft', hp='1 to 3 ft', wp='1 to 2 ft', rate='Fast', life='One season (annual); reseeds freely',
    zl='', zh='', zn='An annual: grows from seed after the last frost and dies at the first.',
    native='Mexico and Central America; Cosmos sulphureus reaches into northern South America.', cons=NO_IUCN, inv='Reseeds freely in gardens; naturalised in parts of Texas.',
    bloom='Daisy flowers in pink, white and magenta (Cosmos bipinnatus) or orange and yellow (Cosmos sulphureus), summer to frost.', fruit='Thin seeds; not eaten.',
    dh='Not poisonous; the pollen may bother allergy sufferers.', da='Not known to be poisonous to pets.', prop=['Seed, sown directly where it is to grow.'], src=['cosmos'])

P['tradescantia_pallida'] = dict(habit='Trailing evergreen perennial groundcover (spiderwort family)', order='Commelinales', family='Commelinaceae', genus='Tradescantia',
    hg='8 to 12 in', wg='1 to 2 ft, spreading', hp='8 in, trailing', wp='1 to 2 ft', rate='Fast', life='Many years',
    zl='7b', zh='11', zn='The top is killed by frost but it comes back from the roots in spring in Central Texas.',
    native='Eastern Mexico (Tamaulipas to the Yucatán).', cons=NO_IUCN, inv='Can spread from stem bits; it is not listed as invasive in Texas.',
    bloom='Small pink three-petalled flowers that open in the morning, warm months.', fruit='None of note.',
    dh='The sap can cause itchy skin (dermatitis) in sensitive people. Wear gloves when handling a lot of it.',
    da='The sap can irritate pets\' skin, especially bellies and paws, and chewing it may upset the stomach.',
    prop=['Stem cuttings root in days in water or soil.'], src=['pallida'], more=[ASPCA])

P['tradescantia_zebrina'] = dict(P['tradescantia_pallida'], habit='Trailing evergreen perennial (spiderwort family)', hg='6 in', wg='1 to 2 ft, trailing',
    zl='9a', zh='11', zn='Damaged by frost; bring it in, or keep cuttings indoors over winter.',
    native='Southern Mexico and Central America to Colombia.', inv='Has gone wild in frost-free places such as Florida and Hawaii; keep stem bits out of compost and the wild.',
    src=['zebrina'], more=[ASPCA])

P['tradescantia_fluminensis'] = dict(P['tradescantia_zebrina'], native='Southeastern Brazil, Paraguay, Uruguay and Argentina.',
    inv='A serious invasive in Florida, New Zealand and Australia, where it smothers forest floors. Keep stem bits out of compost and the wild.',
    bloom='Small white three-petalled flowers.', src=['fluminensis'])

P['gardenia'] = dict(habit='Evergreen flowering shrub', order='Gentianales', family='Rubiaceae', genus='Gardenia',
    hg='3 to 8 ft', wg='3 to 6 ft', hp='2 to 4 ft', wp='2 to 3 ft', rate='Moderate', life='Decades',
    zl='8a', zh='11', zn='Hardy in Central Texas, though hard freezes can burn leaves. Needs acid soil: the alkaline water here yellows its leaves without iron and sulfur.',
    native='Southern China, Taiwan, Japan, Vietnam and nearby parts of Southeast Asia.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Very fragrant waxy white flowers, late spring to summer.', fruit='Orange fruit used as a dye in Asia; not eaten raw.',
    dh='Not seriously poisonous to people.', da='Toxic to cats and dogs (ASPCA lists gardenia): mild vomiting, diarrhea and hives.',
    prop=['Softwood cuttings in early summer, with rooting hormone, in a humid spot.'], src=['gardenia'], more=[ASPCA])

P['fountain_grass'] = dict(habit='Clumping ornamental grass', order='Poales', family='Poaceae', genus='Cenchrus (formerly Pennisetum)',
    hg='3 to 5 ft in flower', wg='2 to 4 ft', hp='2 to 4 ft', wp='2 to 3 ft', rate='Fast', life='Several years where hardy; usually grown as an annual further north',
    zl='9a', zh='11', zn='The top is killed by frost. In zone 8b to 9a it often comes back from the crown after a mild winter, but not after a hard freeze.',
    native='A cultivated selection. Its relatives come from Africa and the Middle East.', cons='Not applicable: a cultivated plant.',
    inv='Green fountain grass (Cenchrus setaceus) is invasive in the Southwest, including Texas. The purple kind rarely sets viable seed, but cut the plumes before they shed if you see seedlings.',
    bloom='Burgundy plumes, summer to fall.', fruit='Rarely sets seed.', dh='Not poisonous.', da='Not known to be poisonous to pets.',
    prop=['Division of the clump in spring; this kind does not come true from seed.'], src=['fountain'])

P['celosia'] = dict(habit='Annual flower in the amaranth family (plumed or crested)', order='Caryophyllales', family='Amaranthaceae', genus='Celosia',
    hg='8 in to 3 ft (by cultivar)', wg='8 to 18 in', hp='8 in to 2 ft', wp='8 to 12 in', rate='Fast', life='One season (annual)',
    zl='', zh='', zn='An annual: thrives in Texas heat and is killed by frost.',
    native='Uncertain; probably tropical Africa or Asia. Now widespread in the tropics.', cons='Not applicable: garden cultivars.',
    inv='Can be a weed in some tropical countries; not a risk here.', bloom='Feathery plumes or velvety crested "cockscombs" in bright colours, summer to frost.',
    fruit='Tiny shiny black seeds. The young leaves of the species are cooked and eaten as a vegetable in Africa and Asia.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists celosia as non-toxic).', prop=['Seed, sown in warm soil after frost.'], src=['celosia'], more=[ASPCA])

P['iris'] = dict(habit='Perennial from a thick creeping rhizome (bearded iris)', order='Asparagales', family='Iridaceae', genus='Iris',
    hg='2 to 3 ft in flower', wg='1 to 2 ft, spreading', hp='1.5 to 2.5 ft', wp='1 to 1.5 ft', rate='Moderate', life='Decades; divide every 3 to 5 years',
    zl='3', zh='9', zn='Hardy here; it needs some winter cold and a sunny, well-drained spot. Plant the rhizome with its top showing.',
    native='Of garden origin, from species of southern and central Europe and the Mediterranean.', cons='Not applicable: a cultivated hybrid.',
    inv='Not a risk here.', bloom='Large flowers with fuzzy "beards" on the falls, in spring.', fruit='Seed pods if left; not edible.',
    dh='The rhizomes are poisonous if eaten (vomiting, diarrhea); the sap can irritate skin.',
    da='Toxic to cats and dogs (ASPCA lists iris): vomiting, drooling and diarrhea, mostly from the rhizome.',
    prop=['Divide the rhizomes in late summer: cut sections with a fan of leaves, trim the leaves to 6 in, and replant.'], src=['iris'], more=[ASPCA])

P['petunia'] = dict(habit='Tender perennial grown as an annual flower', order='Solanales', family='Solanaceae', genus='Petunia',
    hg='6 to 18 in', wg='1 to 3 ft (trailing kinds wider)', hp='6 to 12 in', wp='1 to 2 ft', rate='Fast', life='One season in practice',
    zl='', zh='', zn='Best in Central Texas from fall to spring; struggles in summer heat. Survives light frost.',
    native='A garden hybrid of two South American species from Argentina, Brazil and Uruguay.', cons='Not applicable: a garden hybrid.', inv='Not a risk here.',
    bloom='Trumpet flowers much of the cool season; Ray Black is near-black.', fruit='Small capsules; not edible.',
    dh='Not poisonous.', da='Non-toxic to cats and dogs (ASPCA lists petunia as non-toxic).',
    prop=['Cuttings (patented cultivars like this one may not be propagated for sale).', 'Seed, for seed strains.'], src=['petunia'], more=[ASPCA])

P['artemisia'] = dict(habit='Silver-leaved aromatic perennial that spreads by rhizomes', order='Asterales', family='Asteraceae', genus='Artemisia',
    hg='1 to 3 ft', wg='2 ft, spreading', hp='1 to 2 ft', wp='1 to 2 ft', rate='Fast; can spread aggressively', life='Many years',
    zl='4', zh='9', zn='A Texas native, fully hardy here. Needs good drainage.', native='Much of North America, from Canada to Mexico, including Central Texas.',
    cons='Common across its range. ' + NO_IUCN, inv='Native, but spreads by underground stems. A pot or edging keeps it in place.',
    bloom='Tiny greyish flowers in late summer, which shed pollen that may bother allergy sufferers.', fruit='Tiny seeds; not eaten.',
    dh='Aromatic oils; not dangerous to handle. Not for eating in quantity (many Artemisia contain thujone).', da='Not known as a pet hazard; large amounts eaten could upset the stomach.',
    prop=['Division in spring.', 'Stem cuttings.', 'Seed.'], src=['artemisia'])

P['monarda'] = dict(habit='Clump-forming perennial wildflower (mint family)', order='Lamiales', family='Lamiaceae', genus='Monarda',
    hg='2 to 4 ft', wg='2 to 3 ft, spreading', hp='1.5 to 3 ft', wp='1.5 to 2 ft', rate='Moderate to fast', life='Many years; divide every few years',
    zl='3', zh='9', zn='Fully hardy here; give it afternoon shade in Texas summers. Watch for powdery mildew.',
    native='Much of North America, from Canada to northern Mexico, including Texas.', cons='Common across its range. ' + NO_IUCN,
    inv='Native; spreads by rhizomes but is easy to pull.', bloom='Lavender pom-pom flowers in late spring to summer; a favourite of bees, butterflies and hummingbirds.',
    fruit='Tiny nutlets; not eaten.', dh='Not poisonous; the leaves make an oregano-like tea.', da='Not known to be poisonous to pets.',
    prop=['Division in spring.', 'Seed.', 'Stem cuttings in early summer.'], src=['monarda'])

P['zexmenia'] = dict(habit='Low, woody-based perennial subshrub (daisy family)', order='Asterales', family='Asteraceae', genus='Wedelia',
    hg='1 to 3 ft', wg='2 to 3 ft', hp='1 to 2 ft', wp='1 to 2 ft', rate='Moderate', life='Many years',
    zl='8a', zh='11', zn='A Texas native, hardy here. Cut back in late winter.', native='Central and South Texas and northeastern Mexico.', cons=NO_IUCN + ' Common in its range.',
    inv='Native.', bloom='Orange-yellow daisy flowers from spring to fall; drought and deer tolerant.', fruit='Small seeds that birds eat.',
    dh='Not known to be poisonous; the leaves are rough to the touch.', da='Not known to be poisonous to pets.',
    prop=['Seed.', 'Softwood cuttings.'], src=['zexmenia'])

P['hibiscus_coccineus'] = dict(habit='Herbaceous perennial that dies to the ground each winter', order='Malvales', family='Malvaceae', genus='Hibiscus',
    hg='4 to 8 ft', wg='2 to 4 ft', hp='3 to 5 ft', wp='2 to 3 ft', rate='Fast each summer', life='Many years',
    zl='6a', zh='10', zn='Hardy here: it dies back in winter and resprouts in late spring. Mark its spot so it is not dug up.',
    native='The southeastern US coastal plain: Georgia, Florida, Alabama and Louisiana, in marshes and swamps.', cons=NO_IUCN, inv='Not a risk here.',
    bloom='Large scarlet flowers with five separate petals, summer to fall; each lasts one day.', fruit='Seed capsules; not edible.',
    dh='Not poisonous; the flowers are edible.', da='Not known to be poisonous to pets.', prop=['Seed, nicked or soaked first.', 'Stem cuttings in summer.', 'Division in spring.'],
    src=['hibiscus'])

P['vanilla'] = dict(habit='Climbing orchid vine with fleshy stems and aerial roots', order='Asparagales', family='Orchidaceae', genus='Vanilla',
    hg='Climbs 30 ft or more on trees', wg='Spreads widely', hp='Needs a 6 ft or taller support', wp='1 to 2 ft', rate='Fast in warm, humid conditions', life='Decades',
    zl='11', zh='12', zn='Damaged below about 50°F; a houseplant here.',
    native='Mexico, Central America, Colombia and Brazil, in humid tropical forest.', cons='Endangered (IUCN; wild plants). All orchids are also on CITES Appendix II.',
    inv='Not a risk here.', bloom='Pale greenish-yellow flowers, usually only on vines several years old and over 10 ft long; each lasts one morning.',
    fruit='The vanilla bean: a long pod that needs hand pollination and months of curing.',
    dh='The sap of fresh stems can irritate skin in some people. Cured vanilla pods are food.', da='Not known to be poisonous to pets.',
    prop=['Stem cuttings with at least 3 nodes; lay the lower nodes on moist mix or tie them to a moss support.'], src=['vanilla'], more=[ASPCA])

P['water_hyacinth'] = dict(habit='Floating aquatic perennial', order='Commelinales', family='Pontederiaceae', genus='Pontederia (formerly Eichhornia)',
    hg='6 to 18 in above the water', wg='Spreads over the water surface', hp='Grows in a tub', wp='Fills a tub', rate='Extremely fast: can double in about two weeks', life='Many years where frost-free',
    zl='9a', zh='11', zn='Killed by hard frost.', native='The Amazon basin of South America.', cons=NO_IUCN + ' It is one of the worst invasive species outside its native range.',
    inv='One of the world\'s worst aquatic weeds. It is on the Texas Parks and Wildlife list of prohibited exotic species, which as a rule may not be kept, sold or moved in Texas without a permit. Never put plants or their water in a drain, ditch, creek or pond.',
    bloom='Spikes of lavender flowers with a yellow spot.', fruit='Seed capsules under water; seeds can live for years.',
    dh='Not poisonous to handle.', da='Not known to be poisonous; livestock eat it.', prop=['Daughter plants on runners. Because it is a prohibited species in Texas, do not share or move it.'],
    src=['hyacinth'])

P['cucurbit'] = dict(habit='Annual climbing vine in the gourd family (species not identified yet)', order='Cucurbitales', family='Cucurbitaceae', genus='Not identified yet',
    hg='Climbs 6 to 20 ft by kind', wg='Spreads widely', hp='Climbs a trellis', wp='2 to 4 ft', rate='Very fast', life='One season (annual)',
    zl='', zh='', zn='Killed by frost.', native='Not known until it is identified.', cons='Not applicable.', inv='Not a risk here.',
    bloom='Yellow or white flowers; separate male and female flowers on most kinds.',
    fruit='Do not eat the fruit until it is identified: some gourds contain bitter cucurbitacins that cause severe vomiting and diarrhea. A very bitter taste means spit it out.',
    dh='Fruit of unknown gourds can be poisonous (see Fruit).', da='Keep pets from the fruit until it is identified.', prop=['Seed from ripe fruit.'], src=[])

P['unknown'] = dict(habit='Not identified yet', kingdom='Plantae', dh='Unknown until it is identified: do not eat it, and wash your hands after handling it.',
    da='Unknown until it is identified: keep pets from chewing it.', src=[])

MAP = {  # plant code -> profile
    'P-001': 'dieffenbachia', 'P-010': 'dieffenbachia', 'P-002': 'myrtillocactus', 'P-044': 'myrtillocactus', 'P-003': 'ficus_carica', 'P-004': 'grape',
    'P-005': 'ipomoea_hederacea', 'P-006': 'ipomoea_batatas', 'P-007': 'caesalpinia', 'P-008': 'bougainvillea', 'P-009': 'philo_hybrid', 'P-039': 'philo_hybrid',
    'P-055': 'philo_hybrid', 'P-081': 'philo_hybrid', 'P-011': 'spathiphyllum', 'P-034': 'spathiphyllum', 'P-012': 'aeonium_haworthii', 'P-045': 'aeonium_arboreum',
    'P-013': 'opuntia', 'P-014': 'aloe_vera', 'P-078': 'aloe_vera', 'P-079': 'aloe_vera', 'P-080': 'aloe_dwarf', 'P-015': 'aloiampelos', 'P-016': 'haworthiopsis',
    'P-043': 'haworthiopsis', 'P-017': 'ravenea', 'P-076': 'ravenea', 'P-077': 'ravenea', 'P-018': 'graptosedum', 'P-019': 'portulacaria', 'P-020': 'ficus_lyrata',
    'P-021': 'adenium', 'P-022': 'rose_flori', 'P-073': 'rose_mini', 'P-074': 'rose_mini', 'P-075': 'rose_mini', 'P-023': 'cosmos', 'P-024': 'nephrolepis',
    'P-025': 'begonia', 'P-026': 'begonia', 'P-027': 'coleus', 'P-033': 'coleus', 'P-028': 'aglaonema', 'P-029': 'philo_erubescens', 'P-030': 'philo_erubescens',
    'P-035': 'philo_erubescens', 'P-062': 'philo_erubescens', 'P-031': 'calathea', 'P-032': 'phalaenopsis', 'P-036': 'unknown', 'P-037': 'zz', 'P-038': 'zz',
    'P-040': 'euphorbia_milii', 'P-041': 'moon_cactus', 'P-042': 'agave', 'P-046': 'vanilla', 'P-047': 'tradescantia_pallida', 'P-048': 'syngonium', 'P-060': 'syngonium',
    'P-049': 'monstera', 'P-050': 'water_hyacinth', 'P-051': 'tradescantia_fluminensis', 'P-052': 'gardenia', 'P-053': 'cucurbit', 'P-054': 'fountain_grass',
    'P-056': 'alocasia', 'P-061': 'alocasia', 'P-057': 'celosia', 'P-058': 'celosia', 'P-067': 'celosia', 'P-059': 'tradescantia_zebrina', 'P-063': 'pachira',
    'P-064': 'iris', 'P-065': 'ficus_elastica', 'P-066': 'philo_micans', 'P-068': 'petunia', 'P-069': 'artemisia', 'P-070': 'monarda', 'P-071': 'zexmenia',
    'P-072': 'hibiscus_coccineus',
}
