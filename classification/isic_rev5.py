"""
classification/isic_rev5.py

Authoritative ISIC Revision 5 reference data (sections + 2-digit divisions).
Generated from the UN Statistics Division structure file:
  https://unstats.un.org/unsd/classifications/Econ/isic
  (ISIC_Rev_5_english_structure.csv, kept in classification/data/)

Part 2 classifies each project/file down to the DIVISION level (2-digit code).
"""

# (code, title, section_letter, section_title)
DIVISIONS = [
    ('01', 'Crop and animal production, hunting and related service activities', 'A', 'Agriculture, forestry and fishing'),
    ('02', 'Forestry and logging', 'A', 'Agriculture, forestry and fishing'),
    ('03', 'Fishing and aquaculture', 'A', 'Agriculture, forestry and fishing'),
    ('05', 'Mining of coal and lignite', 'B', 'Mining and quarrying'),
    ('06', 'Extraction of crude petroleum and natural gas', 'B', 'Mining and quarrying'),
    ('07', 'Mining of metal ores', 'B', 'Mining and quarrying'),
    ('08', 'Other mining and quarrying', 'B', 'Mining and quarrying'),
    ('09', 'Mining support service activities', 'B', 'Mining and quarrying'),
    ('10', 'Manufacture of food products', 'C', 'Manufacturing'),
    ('11', 'Manufacture of beverages', 'C', 'Manufacturing'),
    ('12', 'Manufacture of tobacco products', 'C', 'Manufacturing'),
    ('13', 'Manufacture of textiles', 'C', 'Manufacturing'),
    ('14', 'Manufacture of wearing apparel', 'C', 'Manufacturing'),
    ('15', 'Manufacture of leather and related products', 'C', 'Manufacturing'),
    ('16', 'Manufacture of wood and of products of wood and cork, except furniture; manufacture of articles of straw and plaiting materials', 'C', 'Manufacturing'),
    ('17', 'Manufacture of paper and paper products', 'C', 'Manufacturing'),
    ('18', 'Printing and reproduction of recorded media', 'C', 'Manufacturing'),
    ('19', 'Manufacture of coke and refined petroleum products', 'C', 'Manufacturing'),
    ('20', 'Manufacture of chemicals and chemical products', 'C', 'Manufacturing'),
    ('21', 'Manufacture of basic pharmaceutical products and pharmaceutical preparations', 'C', 'Manufacturing'),
    ('22', 'Manufacture of rubber and plastic products', 'C', 'Manufacturing'),
    ('23', 'Manufacture of other non-metallic mineral products', 'C', 'Manufacturing'),
    ('24', 'Manufacture of basic metals', 'C', 'Manufacturing'),
    ('25', 'Manufacture of fabricated metal products, except machinery and equipment', 'C', 'Manufacturing'),
    ('26', 'Manufacture of computer, electronic and optical products', 'C', 'Manufacturing'),
    ('27', 'Manufacture of electrical equipment', 'C', 'Manufacturing'),
    ('28', 'Manufacture of machinery and equipment n.e.c.', 'C', 'Manufacturing'),
    ('29', 'Manufacture of motor vehicles, trailers and semi-trailers', 'C', 'Manufacturing'),
    ('30', 'Manufacture of other transport equipment', 'C', 'Manufacturing'),
    ('31', 'Manufacture of furniture', 'C', 'Manufacturing'),
    ('32', 'Other manufacturing', 'C', 'Manufacturing'),
    ('33', 'Repair, maintenance and installation of machinery and equipment', 'C', 'Manufacturing'),
    ('35', 'Electricity, gas, steam and air conditioning supply', 'D', 'Electricity, gas, steam and air conditioning supply'),
    ('36', 'Water collection, treatment and supply', 'E', 'Water supply; sewerage, waste management and remediation activities'),
    ('37', 'Sewerage', 'E', 'Water supply; sewerage, waste management and remediation activities'),
    ('38', 'Waste collection, treatment and disposal, and recovery activities', 'E', 'Water supply; sewerage, waste management and remediation activities'),
    ('39', 'Remediation and other waste management service activities', 'E', 'Water supply; sewerage, waste management and remediation activities'),
    ('41', 'Construction of residential and non-residential buildings', 'F', 'Construction'),
    ('42', 'Civil engineering', 'F', 'Construction'),
    ('43', 'Specialized construction activities', 'F', 'Construction'),
    ('46', 'Wholesale trade', 'G', 'Wholesale and retail trade'),
    ('47', 'Retail trade', 'G', 'Wholesale and retail trade'),
    ('49', 'Land transport and transport via pipelines', 'H', 'Transportation and storage'),
    ('50', 'Water transport', 'H', 'Transportation and storage'),
    ('51', 'Air transport', 'H', 'Transportation and storage'),
    ('52', 'Warehousing and support activities for transportation', 'H', 'Transportation and storage'),
    ('53', 'Postal and courier activities', 'H', 'Transportation and storage'),
    ('55', 'Accommodation', 'I', 'Accommodation and food service activities'),
    ('56', 'Food and beverage service activities', 'I', 'Accommodation and food service activities'),
    ('58', 'Publishing activities', 'J', 'Publishing, broadcasting, and content production and distribution activities'),
    ('59', 'Motion picture, video and television programme production, sound recording and music publishing activities', 'J', 'Publishing, broadcasting, and content production and distribution activities'),
    ('60', 'Programming, broadcasting, news agency and other content distribution activities', 'J', 'Publishing, broadcasting, and content production and distribution activities'),
    ('61', 'Telecommunications', 'K', 'Telecommunications, computer programming, consultancy, computing infrastructure, and other information service activities'),
    ('62', 'Computer programming, consultancy and related activities', 'K', 'Telecommunications, computer programming, consultancy, computing infrastructure, and other information service activities'),
    ('63', 'Computing infrastructure, data processing, hosting, and other information service activities', 'K', 'Telecommunications, computer programming, consultancy, computing infrastructure, and other information service activities'),
    ('64', 'Financial service activities, except insurance and pension funding', 'L', 'Financial and insurance activities'),
    ('65', 'Insurance, reinsurance and pension funding, except compulsory social security', 'L', 'Financial and insurance activities'),
    ('66', 'Activities auxiliary to financial service and insurance activities', 'L', 'Financial and insurance activities'),
    ('68', 'Real estate activities', 'M', 'Real estate activities'),
    ('69', 'Legal and accounting activities', 'N', 'Professional, scientific and technical activities'),
    ('70', 'Activities of head offices; management consultancy activities', 'N', 'Professional, scientific and technical activities'),
    ('71', 'Architectural and engineering activities; technical testing and analysis', 'N', 'Professional, scientific and technical activities'),
    ('72', 'Scientific research and development', 'N', 'Professional, scientific and technical activities'),
    ('73', 'Activities of advertising, market research and public relations', 'N', 'Professional, scientific and technical activities'),
    ('74', 'Other professional, scientific and technical activities', 'N', 'Professional, scientific and technical activities'),
    ('75', 'Veterinary activities', 'N', 'Professional, scientific and technical activities'),
    ('77', 'Rental and leasing activities', 'O', 'Administrative and support service activities'),
    ('78', 'Employment activities', 'O', 'Administrative and support service activities'),
    ('79', 'Travel agency, tour operator, and other travel related activities', 'O', 'Administrative and support service activities'),
    ('80', 'Investigation and security activities', 'O', 'Administrative and support service activities'),
    ('81', 'Services to buildings and landscape activities', 'O', 'Administrative and support service activities'),
    ('82', 'Office administrative, office support and other business support activities', 'O', 'Administrative and support service activities'),
    ('84', 'Public administration and defence; compulsory social security', 'P', 'Public administration and defence; compulsory social security'),
    ('85', 'Education', 'Q', 'Education'),
    ('86', 'Human health activities', 'R', 'Human health and social work activities'),
    ('87', 'Residential care activities', 'R', 'Human health and social work activities'),
    ('88', 'Social work activities without accommodation', 'R', 'Human health and social work activities'),
    ('90', 'Arts creation and performing arts activities', 'S', 'Arts, sports and recreation'),
    ('91', 'Library, archives, museum and other cultural activities', 'S', 'Arts, sports and recreation'),
    ('92', 'Gambling and betting activities', 'S', 'Arts, sports and recreation'),
    ('93', 'Sports activities and amusement and recreation activities', 'S', 'Arts, sports and recreation'),
    ('94', 'Activities of membership organizations', 'T', 'Other service activities'),
    ('95', 'Repair and maintenance of computers, personal and household goods, and motor vehicles and motorcycles', 'T', 'Other service activities'),
    ('96', 'Personal service activities', 'T', 'Other service activities'),
    ('97', 'Activities of households as employers of domestic personnel', 'U', 'Activities of households as employers; undifferentiated goods- and services-producing activities of households for own use'),
    ('98', 'Undifferentiated goods- and services-producing activities of private households for own use', 'U', 'Activities of households as employers; undifferentiated goods- and services-producing activities of households for own use'),
    ('99', 'Activities of extraterritorial organizations and bodies', 'V', 'Activities of extraterritorial organizations and bodies'),
]

DIVISION_TITLE = {code: title for code, title, _s, _st in DIVISIONS}
DIVISION_SECTION = {code: sec for code, _t, sec, _st in DIVISIONS}
SECTION_TITLE = {sec: st for _c, _t, sec, st in DIVISIONS}

VALID_DIVISIONS = set(DIVISION_TITLE)


def is_valid_division(code: str) -> bool:
    return code in VALID_DIVISIONS


def label(code):
    """Return a human-readable 'NN - Title' label, or None for unclassified."""
    if code is None:
        return None
    return f"{code} - {DIVISION_TITLE.get(code, 'Unknown')}"
