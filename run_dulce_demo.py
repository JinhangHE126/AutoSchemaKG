import os
from openai import OpenAI
from atlas_rag.llm_generator import LLMGenerator
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
model_name = "deepseek-chat"
llm = LLMGenerator(client=client, model_name=model_name)

config = ProcessingConfig(
    model_path=model_name,
    data_directory="example/example_data",
    filename_pattern="Dulce",
    output_directory="example/generated/dulce_demo",
    batch_size_triple=2,
    batch_size_concept=8,
    max_workers=2,
    remove_doc_spaces=True,
    include_concept=True,
)

kg = KnowledgeGraphExtractor(model=llm, config=config)

kg.run_extraction()
kg.convert_json_to_csv()
kg.generate_concept_csv_temp()
kg.create_concept_csv()
kg.convert_to_graphml()

print("Done. Check example/generated/dulce_demo/")