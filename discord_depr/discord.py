import os
import sys
import time
import json
import pandas as pd

from flask.json import jsonify
from flask import Blueprint, request, make_response
from flask.helpers import send_file
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import SQL
import errors
import mysite.tokens as tokens
import discord.ban_export as ban_export


discord = Blueprint('discord', __name__, template_folder='templates')

@discord.route('/discord/locations/<token>', methods=['GET'])
def get_locations(token):

    verified = tokens.verify_token(token=token, verifcation='hiscores')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    players = request.get_json()

    if players is None:
        return jsonify({'Invalid Data':'Data'})

    players = players['names']
    data = SQL.get_player_report_locations(players)
    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/region/<token>', methods=['GET'])
@discord.route('/discord/region/<token>/<regionName>', methods=['GET'])
def get_regions(token, regionName=None):

    verified = tokens.verify_token(token=token, verifcation='hiscores')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})
        
    if regionName is None:
        regionName = request.get_json()

        if regionName is None:
            return jsonify({'Invalid Data':'Data'})

        regionName = regionName['region']
    
    data = SQL.get_region_search(regionName)

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/get_regions/<token>', methods=['GET'])
def get_all_regions(token):

    verified = tokens.verify_token(token=token, verifcation='hiscores')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})
    
    data = SQL.get_all_regions()

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/heatmap/<token>', methods=['GET'])
@discord.route('/discord/heatmap/<token>/<region_id>', methods=['GET'])
def get_heatmap_data(token, region_id=None):
    verified = tokens.verify_token(token=token, verifcation='hiscores')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})
    if region_id is None:
        region_id = request.get_json()

        if region_id is None:
            return jsonify({'Invalid Data':'Data'})

        region_id = region_id['region_id']
    
    data = SQL.get_report_data_heatmap(region_id)


    df = pd.DataFrame(data)

    #Filter out heatmap data from before the bulk of our v1.3 fixes
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d')
    df = df.loc[(df['timestamp'] >= '2021-05-16')]

    #Remove unnecessary columns
    df = df.drop(columns=['z_coord', 'region_id', 'timestamp'])

    #Group by tiles
    df = df.groupby(["x_coord", "y_coord"], as_index=False).sum()
    df = df.astype({"confirmed_ban": int})

    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/player_bans/<token>', methods=['GET'])
@discord.route('/discord/player_bans/<token>/<discord_id>', methods=['GET'])
def get_player_bans(token, discord_id=None):

    verified = tokens.verify_token(token=token, verifcation='hiscores')

    if not (verified):
        return jsonify({'error':'Invalid data'}), 401

    if discord_id is None:
        if isinstance(request.json, str):
            req_data = json.loads(request.json)
        else:
            req_data = request.json
    
        if req_data is None:
            return jsonify({'error':'No data provided.'}), 400

        discord_id = req_data.get("discord_id")

        if discord_id is None:
            return jsonify({'error':'No Discord ID provided.'}), 400

    linked_accounts = SQL.get_discord_linked_accounts(discord_id=discord_id)

    if len(linked_accounts) == 0:
        return jsonify({"error": "User has no OSRS accounts linked to their Discord ID."}), 500

    try:
        download_url = ban_export.create_ban_export(
            file_type=req_data["file_type"],
            linked_accounts=linked_accounts,
            display_name=req_data["display_name"],
            discord_id=req_data["discord_id"]
        )
    except errors.InvalidFileType:
        return jsonify({"error": "File type specified was not valid."}), 400
    except errors.NoDataAvailable:
        return jsonify({"error": "No ban data available for the linked account(s). Possibly the server timed out."}), 500

    return jsonify({"url": download_url})


@discord.route('/discord/download_export/<export_id>')
def download_export(export_id=None):
    if export_id is None:
        return jsonify({"error": "Please provide a valid download ID."}), 400

    download_data = SQL.get_export_links(export_id)

    if len(download_data) == 0:
        return jsonify({"error": "The URL you've provided is invalid."}), 500

    file_path = f"{os.getcwd()}/exports/{download_data[0].file_name}"

    if os.path.exists(file_path):

        update_info = {
            "id": download_data[0].id,
            "time_redeemed": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
            "is_redeemed": 1
        }

        SQL.update_export_links(update_export=update_info)

        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File is no longer present on our system. Please use !excelban or !csvban and try again with a new URL."}), 500
  

@discord.route('/discord/verify/player_rsn_discord_account_status/<token>/<player_name>', methods=['GET'])
def get_verification_status_information(token, player_name=None):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if player_name is None:
        return jsonify({'Invalid Name':'Invalid Name'})
    
    data = SQL.get_verification_info(player_name)

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/verify/playerid/<token>/<player_name>', methods=['GET'])
def get_verification_playerid_information(token, player_name=None):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if player_name is None:
        return jsonify({'Invalid Name':'Invalid Name'})
    
    data = SQL.get_verification_player_id(player_name)

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/verify/verified_player_info/<token>/<player_name>', methods=['GET'])
def get_verified_player_list_information(token, player_name=None):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if player_name is None:
        return jsonify({'Invalid Name':'Invalid Name'})
    
    data = SQL.get_verified_info(player_name)

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)

@discord.route('/discord/verify/insert_player_dpc/<token>/<discord_id>/<player_id>/<code>', methods=['POST', 'OPTIONS'])
def post_verified_insert_information(token, discord_id=None, player_id=None, code=None):

    #Preflight
    if request.method == 'OPTIONS':
        response = make_response()
        header = response.headers
        header['Access-Control-Allow-Origin'] = '*'
        return response

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if discord_id is None:
        return jsonify({'Invalid Discord':'Invalid Discord ID'})

    if player_id is None:
        return jsonify({'Invalid Player ID':'Invalid Player ID'})

    if code is None:
        return jsonify({'Invalid Code':'Invalid Code'})

    token_id = SQL.get_token(token).id
    
    data = SQL.verificationInsert(discord_id, player_id, code, token_id)

    return jsonify({'Value':f'{discord_id} {player_id} {code} Submitted'})


@discord.route('/discord/get_linked_accounts/<token>/<discord_id>', methods=['GET'])
def get_discord_linked_accounts(token, discord_id=None):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if discord_id is None:
        return jsonify({'Invalid Name':'Invalid Name'})
    
    data = SQL.get_discord_linked_accounts(discord_id)

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)


@discord.route('/discord/get_all_linked_ids/<token>', methods=['GET'])
def get_all_linked_ids(token):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})
    
    data = SQL.get_all_verified_ids()

    df = pd.DataFrame(data)
    output = df.to_dict('records')

    return jsonify(output)


@discord.route('/discord/get_latest_sighting/<token>', methods=['GET'])
def get_latest_sighting(token):

    verified = tokens.verify_token(token=token, verifcation='verify_players')

    if not (verified):
        return jsonify({'Invalid Data':'Data'})

    if isinstance(request.json, str):
        req_data = json.loads(request.json)
    else:
        req_data = request.json

    player_id = SQL.get_player(req_data["player_name"]).id
    
    last_sighting_data = SQL.user_latest_sighting(player_id)

    df = pd.DataFrame(last_sighting_data)

    df = df[[  "equip_head_id",
	            "equip_amulet_id",
	            "equip_torso_id",
	            "equip_legs_id",
	            "equip_boots_id",
	            "equip_cape_id",
	            "equip_hands_id",
	            "equip_weapon_id",
                "equip_shield_id"
            ]]

    output = df.to_dict('records')
    output = output[0]

    return jsonify(output)