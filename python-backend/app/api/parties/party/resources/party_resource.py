import uuid

from flask import request
from flask_restplus import Resource, reqparse

from ..models.party import Party
from app.extensions import api
from ....utils.access_decorators import requires_role_mine_view, requires_role_mine_create
from ....utils.resources_mixins import UserMixin, ErrorMixin


class PartyResource(Resource, UserMixin, ErrorMixin):
    parser = reqparse.RequestParser()
    parser.add_argument(
        'first_name', type=str, help='First name of the party, if the party is a person.')
    parser.add_argument(
        'party_name',
        type=str,
        help='Last name of the party (Person), or the Organization name (Organization).')
    parser.add_argument(
        'phone_no', type=str, help='The phone number of the party. Ex: 123-123-1234')
    parser.add_argument('phone_ext', type=str, help='The extension of the phone number. Ex: 1234')
    parser.add_argument('email', type=str, help='The email of the party.')
    parser.add_argument('type', type=str, help='The type of the party. Ex: PER')
    parser.add_argument('suite_no', type=str, help='The suite number of the party address. Ex: 123')
    parser.add_argument('address_line_1', type=str, help='The first address line of the party address. Ex: 1234 Foo Road')
    parser.add_argument('address_line_2', type=str, help='The second address line of the party address. Ex: 1234 Foo Road')
    parser.add_argument('city', type=str, help='The city where the party is located. Ex: FooTown')
    parser.add_argument('province_code', type=str, help='The province code where the party is located. Ex: BC')
    parser.add_argument('postal_code', type=str, help='The postal code of the party address. Ex: A0B1C2')

    PARTY_LIST_RESULT_LIMIT = 25

    @api.doc(
        params={
            'party_guid': 'Party guid. If not provided a list of 100 parties will be returned.',
            '?search':
            'Term searched in first name and party name, and 100 parties will be returned.',
            '?type': 'Search will filter for the type indicated.'
        })
    @requires_role_mine_view
    def get(self, party_guid=None):
        if party_guid:
            party = Party.find_by_party_guid(party_guid)
            if party:
                return party.json()
            else:
                return self.create_error_payload(404, 'Party not found'), 404
        else:
            search_term = request.args.get('search')
            search_type = request.args.get('type').upper() if request.args.get('type') else None
            if search_term:
                if search_type in ['PER', 'ORG']:
                    parties = Party.search_by_name(search_term, search_type,
                                                   self.PARTY_LIST_RESULT_LIMIT)
                else:
                    parties = Party.search_by_name(
                        search_term, query_limit=self.PARTY_LIST_RESULT_LIMIT)
            else:
                parties = Party.query.limit(self.PARTY_LIST_RESULT_LIMIT).all()
            return {'parties': list(map(lambda x: x.json(), parties))}

    @api.expect(parser)
    @requires_role_mine_create
    def post(self, party_guid=None):
        if party_guid:
            self.raise_error(400, 'Error: Unexpected party id in Url.')
        data = PartyResource.parser.parse_args()

        # TODO: Move this logic to somewhere more appropriate
        party_type_code = data['type']
        first_name = data.get('first_name')
        party_name = data['party_name']

        if party_type_code == 'PER':
            # TODO: validate PER method on model
            if not first_name:
                self.raise_error(400, 'Error: Party first name is not provided.')
            party_exists = Party.find_by_name(first_name, party_name)
            if party_exists:
                self.raise_error(
                    400, 'Error: Party with the name: {} {} already exists'.format(
                        first_name, party_name))

        elif party_type_code == 'ORG':
            # TODO: validate ORG method on model
            party_exists = Party.find_by_party_name(party_name)
            if party_exists:
                self.raise_error(
                    400, 'Error: Party with the party name: {} already exists'.format(party_name))
        else:
            self.raise_error(400, 'Error: Party type is not provided.')



        # This part is fine
        try:
            party = Party.create(party_name,
                                 data['email'],
                                 data['phone_no'],
                                 party_type_code,
                                 self.get_create_update_dict(),
                                 # Optional fields
                                 first_name=first_name,
                                 phone_ext=data.get('phone_ext'),
                                 suite_no=data.get('suite_no'),
                                 address_line_1=data.get('address_line_1'),
                                 address_line_2=data.get('address_line_2'),
                                 city=data.get('city'),
                                 province_code=data.get('province_code'),
                                 postal_code=data.get('postal_code'))
        except AssertionError as e:
                    self.raise_error(400, 'Error: {}'.format(e))

        if not party:
            self.raise_error(400, 'Error: Failed to create party')

        party.save()
        return party.json()

    @api.expect(parser)
    @requires_role_mine_create
    def put(self, party_guid):
        data = PartyResource.parser.parse_args()
        party_exists = Party.find_by_party_guid(party_guid)
        if not party_exists:
            return self.create_error_payload(404, 'Party not found'), 404
        party_type_code = data.get('type')
        if party_type_code == 'PER':
            first_name = data.get('first_name', party_exists.first_name)
            party_name = data.get('party_name', party_exists.party_name)
            party_name_exists = Party.find_by_name(first_name, party_name)
            if party_name_exists:
                self.raise_error(
                    400, 'Error: Party with the name: {} {} already exists'.format(
                        first_name, party_name))
            party_exists.first_name = first_name
            party_exists.party_name = party_name
        elif party_type_code == 'ORG':
            party_name = data.get('party_name', party_exists.party_name)
            party_name_exists = Party.find_by_party_name(party_name)
            if party_name_exists:
                self.raise_error(400,
                                 'Error: Party with the name: {} already exists'.format(party_name))
            party_exists.party_name = party_name
        else:
            self.raise_error(400, 'Error: Party type is not provided.')
        party_exists.save()
        return party_exists.json()
