# important notice
# Note that this directory needs to be put in the same directory of stanford-corenlp-full-2017-06-09
import os
from utils import *
from PythonNLPCore.NLPCore import NLPCoreClient
from enum import Enum

STANFORD_NLP_PATH = os.path.abspath(os.path.dirname(__file__)) + '/../' + 'stanford-corenlp-full-2017-06-09'
TEXT = []
PIPELINE1_PROPERTIES = {
    "annotators": "tokenize,ssplit,pos,lemma,ner", # note that compare to instruction, we can add 'relation' here
    "parse.model": "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
    "ner.useSUTime": "0"
}
PIPELINE2_PROPERTIES_WITH_RELATION = {
    "annotators": "tokenize,ssplit,pos,lemma,ner,parse,relation",  # compare to instruction, we add 'relation' here
    "parse.model": "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
    "ner.useSUTime": "0"
}
PIPELINE2_PROPERTIES_WITHOUT_RELATION = {
    "annotators": "tokenize,ssplit,pos,lemma,ner,parse",
    "parse.model": "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
    "ner.useSUTime": "0"
}
SINGLE_PIPELINE_ENTRIES = []
RELATION_FLAG = ''


def find_relation_noun(val):
    return {
        'Live_In': ['PEOPLE', 'LOCATION'],
        'Located_In': ['LOCATION', 'LOCATION'],
        'OrgBased_In': ['ORGANIZATION', 'LOCATION'],
        'Work_For': ['ORGANIZATION', 'PEOPLE']
    }.get(val, [])


def set_text(text):
    global TEXT
    del TEXT[:]
    TEXT.append(text)


def nlp(relation_flag, confidence_threshold):
    global SINGLE_PIPELINE_ENTRIES, RELATION_FLAG
    RELATION_FLAG = relation_flag
    SINGLE_PIPELINE_ENTRIES = []
    # path to core nlp
    try:
        nlp_core_client = NLPCoreClient(STANFORD_NLP_PATH)
    except FileNotFoundError:
        print("Stanfold NLP Suite not found")
        print("Please put Stanfold NLP Directory and IterativeSetExpansion in same directory")
        return
    return pipeline(nlp_core_client, relation_flag, confidence_threshold)


def pipeline(client, relation_flag, confidence_threshold):
    doc = client.annotate(text=TEXT, properties=PIPELINE1_PROPERTIES)
    # first send TEXT through pipeline1
    for sentence in doc.sentences:
        # TODO: take care of unicode
        # naive implementation
        selected_sentence = ''
        # recover sentence from pipeline1
        for token in sentence.tokens:
            selected_sentence += ' ' + token.word
        # send each sentence to pipeline2
        pipeline2(client, selected_sentence, relation_flag, confidence_threshold)
    return SINGLE_PIPELINE_ENTRIES


def valid_relation(relation, relation_flag):
    if relation == []:
        return False
    if relation_flag not in relation.probabilities:
        return False
    for entity in relation.entities:
        if str(entity.type).strip() == 'O': # it's not '0' it's 'O'
            return False
    return True


def relation_confidence_too_low(relation, relation_flag, confidence_threshold):
    """
    this function determines if the confidence of relation_flag is strong enough to output
    :param relation: the relation
    :param relation_flag: the type we are looking for, e.g. 'Work_for'
    :param confidence_threshold: confidence_threshold
    :return: a bool
    """
    flag_conf = float(relation.probabilities[relation_flag])
    confidence_list = [float(relation.probabilities[t]) for t in ['_NR', 'OrgBased_In', 'Live_In', 'Located_In', 'Work_For']]
    # return if the conf of the relation type we designated is not the highest among all types
    return sorted(confidence_list, reverse=True).index(flag_conf) != 0


def relation_does_not_conform_to_type(highest_relation):
    """
    determine if this highest_relation does not produce the relation we want
    :param highest_relation:
    :return:
    """
    nouns = find_relation_noun(RELATION_FLAG)
    types = []
    for i in range(len(highest_relation.entities)):
         types.append(str(highest_relation.entities[i].type))
    return types != nouns and types[::-1] != nouns


def pipeline2(client, selected_sentence, relation_flag, confidence_threshold):
    # pipeline 2 to extract relations from @param selected_sentences generated by pipeline 1
    global SINGLE_PIPELINE_ENTRIES
    this_sentence_list = [selected_sentence]
    doc2 = client.annotate(text=this_sentence_list, properties=PIPELINE2_PROPERTIES_WITH_RELATION)
    processed_sentence = doc2.sentences[0] # notice that doc2.sentences only have one sentence
    # find the relation within relation set that has the highest relation_flag value
    # del non-applicable relations
    valid_relations = []
    for relation in processed_sentence.relations:
        if valid_relation(relation, relation_flag):
            valid_relations.append(relation)
    if len(valid_relations) == 0:
        return
    valid_relations = sorted(valid_relations, key=lambda x: float(x.probabilities[relation_flag]), reverse=True)
    highest_relation = valid_relations[0]
    if relation_confidence_too_low(highest_relation, relation_flag, confidence_threshold) or \
            relation_does_not_conform_to_type(highest_relation):
        return
    entry = {}
    entry['relation'] = relation_flag
    entry['confidence'] = float(highest_relation.probabilities[relation_flag])
    entityType0 = highest_relation.entities[0].type
    entityValue0 = highest_relation.entities[0].value
    entityType1 = highest_relation.entities[1].type
    entityValue1 = highest_relation.entities[1].value
    type0 = find_relation_noun(RELATION_FLAG)[0]
    type1 = find_relation_noun(RELATION_FLAG)[1]
    if entityType0 == type0:
        entry['entityType0'] = entityType0
        entry['entityValue0'] = entityValue0
        entry['entityType1'] = entityType1
        entry['entityValue1'] = entityValue1
    else:
        entry['entityType0'] = entityType1
        entry['entityValue0'] = entityValue1
        entry['entityType1'] = entityType0
        entry['entityValue1'] = entityValue0
    write_annotate_entry(entry, selected_sentence)
    SINGLE_PIPELINE_ENTRIES.append(entry)

    """
    Sample Usage
    """
    # from NLPCore import NLPCoreClient
    # text = ["Bill Gates works at Microsoft.", "Sergei works at Google."]
    # # path to core nlp
    # client = NLPCoreClient('/path/to/stanford-corenlp-full-2017-06-09')
    # properties = {
    #     "annotators": "tokenize,ssplit,pos,lemma,ner,parse,relation",
    #     "parse.model": "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz",
    #     "ner.useSUTime": "0"
    # }
    # doc = client.annotate(text=text, properties=properties)
    # print(doc.sentences[0].relations[0])
    # print(doc.tree_as_string())