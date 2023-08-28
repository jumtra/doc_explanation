from pathlib import Path

from doc_explanation.answer.answer_format import format_return
from doc_explanation.answer.model.ctranslate import CtranslatedModel
from doc_explanation.answer.prompt import PROMPT
from doc_explanation.common.arg_parser import common_parser
from doc_explanation.common.config_manager import ConfigManager
from doc_explanation.common.log_handler import add_log_handler
from doc_explanation.search.doc_search.query import get_search_words
from doc_explanation.search.doc_search.search import sentence_search
from doc_explanation.search.vec_search.search import VectorSearch


def set_args(parser, config_manager: ConfigManager) -> ConfigManager:
    config_manager.config.input.data_path = parser.data_path
    if parser.max_doc is not None:
        config_manager.config.search.doc_search.max_doc = parser.max_doc
    if parser.max_results is not None:
        config_manager.config.search.vec_search.max_results = parser.max_results
    if parser.generate_num is not None:
        config_manager.config.generate.generate_num = parser.generate_num

    return config_manager


def main():
    parser = common_parser()
    logger = add_log_handler(".")
    config_manager = ConfigManager.from_yaml(config_yaml_path="config.yaml", config_dir="doc_explanation/config")

    # set argparse
    config_manager = set_args(parser=parser, config_manager=config_manager)

    path_folder = str(Path(config_manager.config.input.data_path))
    question = parser.question
    logger.info(f"質問：{question}")
    list_words = get_search_words(question)

    # 早期リターン
    if len(list_words) == 0:
        logger.info("検索クエリを生成できませんでした。質問文章を変更してください。")
        return

    log_text = "検索クエリ："
    for word in list_words:
        log_text += word + " "
    logger.info(log_text)

    searched_sentences = sentence_search(path_folder=path_folder, list_words=list_words, max_doc=config_manager.config.search.doc_search.max_doc)

    # 早期リターン
    if searched_sentences.is_not_exist:
        logger.info("検索結果が存在しません。")
        return

    searched_vectors = VectorSearch(
        list_sentence=searched_sentences.list_sentence, embedding_model=config_manager.config.search.vec_search.embedding_model
    )

    list_result = searched_vectors.search_relevant_chunks(text=question, max_results=config_manager.config.search.vec_search.max_results)
    # 早期リターン
    if len(list_result) == 0:
        logger.info("質問の参考になる文章が存在しませんでした。")
        return

    list_result = [{"text": result.text, "num": result.num, "file_name": result.file_name} for result in list_result]
    list_text = [dict_result["text"] for dict_result in list_result]

    result = "".join([t + "\n" for t in list_text])

    # 回答生成
    model = CtranslatedModel(config_manager=config_manager)

    prompt = PROMPT.format(question=question, result=result)
    list_answer = []
    for _ in range(config_manager.config.generate.generate_num):
        text = model.generate(prompt=prompt).split("###回答:")[-1]
        if text != "":
            list_answer.append(text)
    logger.info(f"\n検索結果：{result}")

    if len(list_answer) == 0:
        logger.info(f"\n回答：回答は生成されませんでした。")

    else:
        for i, text in enumerate(list_answer):
            logger.info(f"\n回答{i}：" + text)
    return_text = format_return(question=question, list_answer=list_answer, list_result=list_result)
    logger.info(return_text)


if __name__ == "__main__":
    main()
