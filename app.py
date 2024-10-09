from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
import uuid  # Importando para gerar IDs únicos

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%dT%H:%M')
    return value.strftime(format)


# Caminho do arquivo JSON
JSON_FILE = 'data/cars.json'

# Função para carregar dados do JSON
def load_cars():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as file:
            return json.load(file)
    return []

# Função para salvar dados no JSON
def save_cars(cars):
    with open(JSON_FILE, 'w') as file:
        json.dump(cars, file, indent=4)

# Função para determinar o status do carro (Pronto, Pendente, Entregue)
def get_car_status(car):
    todos_feitos = all(item['status'] == 'Feito' for item in car['acessorios'] + car['servicos_estetica'])
    algum_pendente = any(item['status'] in ['Aguardando Peça', 'Instalando'] for item in car['acessorios'] + car['servicos_estetica'])
    
    if 'entrega' in car and car['entrega'] == 'sim':
        return 'entregue'
    elif todos_feitos:
        return 'pronto'
    elif algum_pendente:
        return 'pendente'
    else:
        return 'indefinido'

# Rota principal para exibir a lista de carros
@app.route('/')
def index():
    cars = load_cars()

    # Atualizando status de cada carro
    for car in cars:
        car['status_geral'] = get_car_status(car)

    # Filtrando os carros que possuem 'data_hora_entrega' e ordenando-os
    cars_with_delivery_date = [car for car in cars if 'data_hora_entrega' in car]
    cars_with_delivery_date.sort(key=lambda car: datetime.strptime(car['data_hora_entrega'], '%Y-%m-%dT%H:%M'))

    # Verificando se há filtros de data
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            cars_with_delivery_date = [
                car for car in cars_with_delivery_date
                if start <= datetime.strptime(car['data_hora_entrega'], '%Y-%m-%dT%H:%M') <= end
            ]
        except ValueError:
            pass  # Se a data estiver incorreta, nenhum filtro será aplicado

    return render_template('index.html', cars=cars_with_delivery_date, start_date=start_date, end_date=end_date)

# Rota para adicionar um carro
@app.route('/add', methods=['GET', 'POST'])
def add_car():
    if request.method == 'POST':
        car = {
            'id': str(uuid.uuid4()),  # Gerando ID único para o carro
            'vendedor': request.form['vendedor'],
            'model': request.form['model'],
            'color': request.form['color'],
            'chassi_reduzido': request.form['chassi_reduzido'],
            'cliente': request.form['cliente'],
            'status_chegada': request.form['status_chegada'],
            'data_hora_entrega': request.form['data_hora_entrega'],
            'acessorios': [],  # Inicializando como lista vazia
            'servicos_estetica': [],  # Inicializando como lista vazia
            'consultor': request.form.get('consultor', ''),  # Campo para o consultor
            'entrega': 'nao'  # Status de entrega inicial
        }

        # Carrega os carros existentes e adiciona o novo carro
        cars = load_cars()
        cars.append(car)
        save_cars(cars)
        return redirect(url_for('index'))

    return render_template('add_car.html')

# Rota para visualizar detalhes do carro e gerenciar informações
@app.route('/car/<string:car_id>', methods=['GET', 'POST'])
def car_details(car_id):
    cars = load_cars()
    car = next((c for c in cars if c['id'] == car_id), None)  # Procurando o carro pelo ID único

    if car:
        # Garantindo que os campos 'acessorios', 'servicos_estetica', 'consultor' e 'entrega' existam
        if 'acessorios' not in car:
            car['acessorios'] = []
        if 'servicos_estetica' not in car:
            car['servicos_estetica'] = []
        if 'consultor' not in car:
            car['consultor'] = ''
        if 'entrega' not in car:
            car['entrega'] = 'nao'

        if request.method == 'POST':
            # Atualizando o status de chegada do carro
            if 'status_chegada' in request.form:
                car['status_chegada'] = request.form['status_chegada']

            # Atualizando a data e hora de entrega
            if 'data_hora_entrega' in request.form:
                car['data_hora_entrega'] = request.form['data_hora_entrega']

            # Atualizando o consultor responsável
            if 'consultor' in request.form:
                car['consultor'] = request.form['consultor']

            # Marcar como entregue
            if 'entrega' in request.form:
                car['entrega'] = request.form['entrega']

            # Adicionando um item (acessório ou serviço de estética)
            if 'descricao' in request.form and 'categoria' in request.form:
                item = {
                    'descricao': request.form['descricao'],
                    'tipo': 'Cortesia',  # Valor padrão ao adicionar
                    'status': 'Aguardando Peça'  # Valor padrão ao adicionar
                }
                if request.form['categoria'] == 'Acessório':
                    car['acessorios'].append(item)
                elif request.form['categoria'] == 'Serviço de Estética':
                    car['servicos_estetica'].append(item)

            # Atualizar tipo e status dos acessórios
            if 'update_acessorio' in request.form:
                acessorio_index = int(request.form['update_acessorio'])
                if 0 <= acessorio_index < len(car['acessorios']):
                    car['acessorios'][acessorio_index]['tipo'] = request.form.get('tipo_acessorio', car['acessorios'][acessorio_index]['tipo'])
                    car['acessorios'][acessorio_index]['status'] = request.form.get('status_acessorio', car['acessorios'][acessorio_index]['status'])

            # Atualizar tipo e status dos serviços de estética
            if 'update_servico' in request.form:
                servico_index = int(request.form['update_servico'])
                if 0 <= servico_index < len(car['servicos_estetica']):
                    car['servicos_estetica'][servico_index]['tipo'] = request.form.get('tipo_servico', car['servicos_estetica'][servico_index]['tipo'])
                    car['servicos_estetica'][servico_index]['status'] = request.form.get('status_servico', car['servicos_estetica'][servico_index]['status'])

            # Remover acessório
            if 'remove_acessorio' in request.form:
                acessorio_index = int(request.form['remove_acessorio'])
                if 0 <= acessorio_index < len(car['acessorios']):
                    del car['acessorios'][acessorio_index]

            # Remover serviço de estética
            if 'remove_servico' in request.form:
                servico_index = int(request.form['remove_servico'])
                if 0 <= servico_index < len(car['servicos_estetica']):
                    del car['servicos_estetica'][servico_index]

            # Salva as alterações no JSON
            save_cars(cars)

        # Renderiza a página de detalhes do carro
        return render_template('details.html', car=car, car_id=car_id)

    # Caso o carro não seja encontrado
    return "Carro não encontrado", 404


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
