from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.db import IntegrityError, models 
from django.http import HttpResponseRedirect
from django.core.exceptions import MultipleObjectsReturned
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.urls import reverse, reverse_lazy
from .models import Comment, Bid, Watchlist
from django.views.generic import (
    ListView,
    CreateView,
    DeleteView,
    UpdateView,
)
from .forms import (
    ListingCreateForm,
    BidForm,
    CommentForm,
    WatchlistForm,
    EndForm,
)
from .models import Listing, Comment, Bid, User
from .services import (
    bid_validate,
     watch_validate,
    validate_single_winner,
    determine_bid_winner,
)


U = get_user_model()


class IndexView(ListView):
    model = Listing
    template_name = "auctions/index.html"
    context_object_name = "context"


def watchlistview(request):

    watchlist = Watchlist.objects.filter(user_id=request.user)
    listing = Listing.objects.all()
    user_lists = []
    watch_lists = []

    for obj in watchlist:
        if obj.user_id == request.user.id:
            watch_lists.append(obj)

    for obj in watch_lists:
        if obj.listing in listing:
            user_lists.append(obj.listing)

    return render(request, "auctions/watchlist.html", {"listing": user_lists})


def Listing_detail(request, slug):
    # the specific listing requested
    list_detail = get_object_or_404(Listing, slug=slug)
    watchlst = Watchlist.objects.filter(user_id=request.user.id) or None
    comment_db = Comment.objects.filter(listing_id=list_detail.id)
    max_bid = Bid.objects.filter(listing_id=list_detail.id).aggregate(models.Max('bid'))

    comment_form = CommentForm(request.POST or None)
    bid_form = BidForm(request.POST or None)
    watchlist_form = WatchlistForm(request.POST or None)

    if list_detail.owner_id == request.user.id:
        end_list = EndForm(request.POST or None)
    else:
        end_list = None

    if list_detail.end_listing():
        if not validate_single_winner(list_detail):
            raise MultipleObjectsReturned("More than one winning bid found")

        else:
            determine_bid_winner(list_detail)
        list_detail.save()

    if request.method == "POST":
        if "comments" in request.POST and comment_form.is_valid():
            new_form = comment_form.save(commit=False)
            new_form.owner = request.user
            new_form.listing_id = list_detail.id
            new_form.save()
            return redirect(
                "auctions:listing_detail",
                slug=slug,
            )
        if "watchlist" in request.POST and watchlist_form.is_valid():
            if watch_validate(list_detail, request.user) and len(watchlst) == 1:
                watchlst[0].active = watchlist_form.cleaned_data["active"]
                watchlst[0].save()

                # watchlist_form.save()

            else:
                new_watch = Watchlist.objects.create(
                    listing_id=list_detail.id, user_id=request.user.id, active=True
                )
                new_watch.save()

            return redirect(
                "auctions:listing_detail",
                slug=slug,
            )
        if "end_list" in request.POST and end_list.is_valid():
            print("maybe")
            list_detail.active = end_list.cleaned_data["active"]
            list_detail.save()
            return redirect(
                "auctions:listing_detail",
                slug=slug,
            )
        if "bids" in request.POST and bid_form.is_valid():

            if bid_form.cleaned_data["bid"] > max_bid.bid and bid_validate(
                bid_form.cleaned_data["bid"], request.user
            ):
                new_bid = bid_form.save(commit=False)
                new_bid.listing_id = list_detail.id
                new_bid.owner_id = request.user.id
                new_bid.save()

            return redirect(
                "auctions:listing_detail",
                slug=slug,
            )

    else:
        return render(
            request,
            "auctions/listing_detail.html",
            {
                "comments": comment_form,
                "watchlist": watchlist_form,
                "listing": list_detail,
                "bids": bid_form,
                "comment_db": comment_db,
                "max_bid": max_bid,
                "end_list": end_list,
            },
        )


class ListingCreate(CreateView):
    model = Listing
    template_name = "auctions/listing_create.html"
    form_class = ListingCreateForm
    # fields = [ 'title', 'image', 'description', 'active', 'start_price', 'auction_length', 'slug']
    success_url = reverse_lazy("auctions:index")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ListingDelete(DeleteView):
    model = Listing
    template_name = "auctions/listing_create.html"
    # need a listing delete form and relevant deletion "are you sure" content
    form_class = ListingCreateForm

    success_url = reverse_lazy("auctions:index")


class ListingUpdate(UpdateView):
    template_name = "auctions/listing_create.html"
    queryset = Listing.objects.all()
    form_class = ListingCreateForm


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("auctions:index"))
        else:
            return render(
                request,
                "auctions/login.html",
                {"message": "Invalid username and/or password."},
            )
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("auctions:index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(
                request, "auctions/register.html", {"message": "Passwords must match."}
            )

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request,
                "auctions/register.html",
                {"message": "Username already taken."},
            )
        login(request, user)
        return HttpResponseRedirect(reverse("auctions:index"))
    else:
        return render(request, "auctions/register.html")



def new_listing_detail(request, slug):
    #can we reduce the number of DB queries here?
    listing = get_object_or_404(Listing, slug=slug)
    current_bid = Bid.objects.filter(listing_id=listing.id).aggregate(models.Max('bid'))
    if current_bid['bid__max'] == None:
        current_bid = {'bid__max': listing.start_price}
        
        
    comment_list = Comment.objects.filter(listing_id=listing.id)
    try:
        watchlist = Watchlist.objects.get(listing_id=listing.id, user_id=request.user)
    except models.ObjectDoesNotExist:
        watchlist = {'active' : False, 'user_id' : request.user, 'listing_id': listing.id }
    bid_form = BidForm(request.POST or None)
    comment_form = CommentForm(request.POST or None)
    watchlist_form = WatchlistForm(request.POST or None, initial={
        'active' : watchlist.active
    }) 
    
    context = {
            'bid_form' : bid_form,
            'comment_form' : comment_form,
            'watchlist_form': watchlist_form,
            'current_bid': current_bid,
            'comment_list': comment_list,
            'watchlist' :  watchlist,
            'listing': listing,
            'user_cash': request.user.cash
        }
    
    if request.method == "POST":
            
        if 'watchlist' in request.POST and watchlist_form.is_valid():
            if watchlist.user == request.user:
                watchlist.active = watchlist_form.cleaned_data['active']
                watchlist.save()
                return redirect('auctions:new_listing_detail', slug=slug)
            return render(request, 'auctions/listing_deets.html', context)
        
        if 'bids' in request.POST and bid_form.is_valid():
            
            if request.user.cash > bid_form.cleaned_data['bid']:
                b = bid_form.save(commit=False)
                b.owner_id = request.user.id
                b.listing_id = listing.id 
                user = request.user
                user.cash = user.cash - b.bid
                user.save()
                b.save()
                return redirect('auctions:new_listing_detail', slug=slug)
            
            messages.error(request, 'You do not have sufficient funds')
            return render(request, 'auctions/listing_deets.html', context)
        
        if 'comment' in request.POST and comment_form.is_valid():
            
            pass
        
    
    return render(request, 'auctions/listing_deets.html', context)